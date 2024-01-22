# Copyright 2018-2021 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#from ctypes import *
import pathlib
from smtk_draco import Decoder

def _load_dll():
    dll_path = pathlib.Path(pathlib.Path(__file__).parent, "extern_draco.dll")
    dll = CDLL(dll_path)

    dll.decoderCreate.restype = c_void_p
    dll.decoderCreate.argtypes = []

    dll.decoderRelease.restype = None
    dll.decoderRelease.argtypes = [c_void_p]

    dll.decoderDecode.restype = c_bool
    dll.decoderDecode.argtypes = [c_void_p, c_void_p, c_size_t]

    dll.decoderReadAttribute.restype = c_bool
    dll.decoderReadAttribute.argtypes = [c_void_p, c_uint32, c_size_t, c_char_p]

    dll.decoderGetVertexCount.restype = c_uint32
    dll.decoderGetVertexCount.argtypes = [c_void_p]

    dll.decoderGetIndexCount.restype = c_uint32
    dll.decoderGetIndexCount.argtypes = [c_void_p]

    dll.decoderAttributeIsNormalized.restype = c_bool
    dll.decoderAttributeIsNormalized.argtypes = [c_void_p, c_uint32]

    dll.decoderGetAttributeByteLength.restype = c_size_t
    dll.decoderGetAttributeByteLength.argtypes = [c_void_p, c_uint32]

    dll.decoderCopyAttribute.restype = None
    dll.decoderCopyAttribute.argtypes = [c_void_p, c_uint32, c_void_p]

    dll.decoderReadIndices.restype = c_bool
    dll.decoderReadIndices.argtypes = [c_void_p, c_size_t]

    dll.decoderGetIndicesByteLength.restype = c_size_t
    dll.decoderGetIndicesByteLength.argtypes = [c_void_p]

    dll.decoderCopyIndices.restype = None
    dll.decoderCopyIndices.argtypes = [c_void_p, c_void_p]

    return dll

def decode_file(file:pathlib.Path|str):

    if isinstance(file, str):
        file = pathlib.Path(file)

    if not file.exists():
        print(f"File {file} does not exist")

    print(f"Loading Draco")
    dll = _load_dll()
    
    print(f"Creating decoder")
    decoder = dll.decoderCreate()

    with open(file, "rb") as f:
        data = f.read()
        if not dll.decoderDecode(decoder, data, len(data)):
            print(f"Error decoding {file}")
            return
    
    vertex_count = dll.decoderGetVertexCount(decoder)
    print( f"Decoded {vertex_count} vertices" )
    
    index_count = dll.decoderGetIndexCount(decoder)
    print( f"Decoded {index_count} indices" )

    print(f"Releasing decoder")
    dll.decoderRelease(decoder)

def decode_primitive(converter, gltf_primitive, gltf_mesh, gltf_data):
    """
    Handles draco compression.
    Moves decoded data into new buffers and buffer views held by the accessors of the given primitive.
    """
    # Get the extension attributes of the primitive
    extension = gltf_primitive["extensions"]["KHR_draco_mesh_compression"]
    draco_buffer_view_index = extension["bufferView"]
    extension_attributes = extension["attributes"]

    print("Draco buffer view index: ", draco_buffer_view_index)
    print("Draco attributes", extension_attributes)

    # Get the compressed primitive from the draco buffer
    draco_buffer_view = gltf_data["bufferViews"][draco_buffer_view_index]
    draco_buffer_index = draco_buffer_view["buffer"]
    draco_buffer = converter.buffers[draco_buffer_index]

    draco_data_length = draco_buffer_view["byteLength"]
    draco_data_start_index = draco_buffer_view["byteOffset"]
    draco_data_end_index = draco_buffer_view["byteOffset"] + draco_data_length

    draco_data = draco_buffer[ draco_data_start_index: draco_data_end_index]
 
    # (Debugging) Save the draco data to a draco file (.drc)
    original_file_path = pathlib.Path(converter.filepath)
    filename = f"{original_file_path.stem}.{draco_buffer_view_index}_{draco_data_start_index}-{draco_data_end_index}.drc"

    filepath = pathlib.Path(original_file_path.parent, filename)
    if filepath.exists():
        print(f"{filepath} already exists")
    else:
        print(f"Saving buffer view {draco_buffer_view_index} of buffer {draco_buffer_index} to {filepath}")            
        with open(filepath, "wb") as f:
            print(f"writing {draco_data_length} bytes to file")
            f.write(draco_data)

    # Decode the draco data
    print("Decoding buffer")
    draco_decoder = Decoder()
    
    if not draco_decoder.decode(draco_data):
        raise RuntimeError("Could not decode mesh")

    # Read indices.
    index_accessor_index = gltf_primitive["indices"]
    index_accessor = gltf_data["accessors"][index_accessor_index]
    if draco_decoder.get_index_count() != index_accessor["count"]:
        print('WARNING', 'Draco Decoder: Index count of accessor and decoded index count does not match. Updating accessor.')
        index_accessor.count = draco_decoder.get_index_count()
    
    if not draco_decoder.read_indices(index_accessor["componentType"]):
        print('ERROR', 'Draco Decoder: Unable to decode indices. Skipping primitive')
        return

    index_buffer_byte_length = draco_decoder.get_index_byte_length()
    decoded_index_buffer = bytes(index_buffer_byte_length)
    draco_decoder.copy_indices(decoded_index_buffer)
    print(f"Loaded index buffer containing {index_buffer_byte_length} bytes")
   


    # Generate a new buffer holding the decoded index data.
    buffer_index = len( converter.buffers.keys() )
    converter.buffers[ buffer_index ] = decoded_index_buffer

    # Create a buffer view referencing the new buffer.
    buffer_view = {
        "buffer": buffer_index,
        "byteLength": index_buffer_byte_length,
        "name": f"index buffer view"
    }
    print("added buffer view ", buffer_view)
    gltf_data["bufferViews"].append(buffer_view)
    buffer_view_index = len( gltf_data["bufferViews"] ) - 1

    # Update accessor to point to the new buffer view.
    index_accessor["byteOffset"] = 0
    index_accessor["bufferView"] = buffer_view_index
    gltf_data["accessors"][index_accessor_index] = index_accessor         
    
    # Read each attribute.
    for attr in extension['attributes']:
        print(f"Processing attribute {attr}")
        dracoId = extension['attributes'][attr]
        if attr not in gltf_primitive["attributes"]:
            print('ERROR', f'Draco Decoder: Draco attribute {attr} not in primitive attributes. Skipping primitive')
            return
        
        accessor_index = gltf_primitive["attributes"][attr]
        accessor = gltf_data["accessors"][accessor_index]
        if draco_decoder.get_vertex_count() != accessor["count"]:
            print('WARNING', f'Draco Decoder: Vertex count of accessor and decoded vertex count does not match for attribute {attr}. Updating accessor.')
            accessor["count"] = draco_decoder.get_vertex_count()
            gltf_data["accessors"][accessor_index] = accessor

        print("Attribute: ", attr)
        print("Draco ID: ", dracoId)
        print("Accessor: ", accessor)

        if not draco_decoder.read_attribute(dracoId, accessor["componentType"], accessor["type"]):
            print('ERROR', f'Draco Decoder: Could not decode attribute {attr}. Skipping primitive')
            return
        
        buffer_size = draco_decoder.get_attribute_byte_length(dracoId)
        decoded_buffer = bytes(buffer_size)
        draco_decoder.copy_attribute(dracoId, decoded_buffer)
        print(f"Loaded {attr} buffer containing {buffer_size} bytes")

        # Generate a new buffer holding the decoded vertex data.
        buffer_index = len( converter.buffers.keys() )
        converter.buffers[ buffer_index ] = decoded_buffer

        # Create a buffer view referencing the new buffer.
        buffer_view = {
            "buffer": buffer_index,
            "byteLength": buffer_size,
            "name": f"{attr} buffer view"
        }
        print("added buffer view ", buffer_view)
        gltf_data["bufferViews"].append(buffer_view)
        buffer_view_index = len( gltf_data["bufferViews"] ) - 1

        # Update accessor to point to the new buffer view.
        accessor["byteOffset"] = 0
        accessor["bufferView"] = buffer_view_index
        gltf_data["accessors"][accessor_index] = accessor
        
if __name__ == "__main__":
    import sys
    decode_file(sys.argv[1])