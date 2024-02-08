from smtk_draco import Decoder

EXTENSION_NAME="KHR_draco_mesh_compression"

def decode_primitive(converter, gltf_primitive, gltf_data):
    """
    Handles draco compression.
    Moves decoded data into new buffers and buffer views held by the accessors of the given primitive.
    """
    # Get the extension attributes of the primitive
    extension = gltf_primitive["extensions"][EXTENSION_NAME]
    draco_buffer_view_index = extension["bufferView"]
    extension_attributes = extension["attributes"]

    # Get the compressed primitive from the draco buffer
    draco_buffer_view = gltf_data["bufferViews"][draco_buffer_view_index]
    draco_buffer_index = draco_buffer_view["buffer"]
    draco_buffer = converter.buffers[draco_buffer_index]

    draco_data_length = draco_buffer_view["byteLength"]
    draco_data_start_index = draco_buffer_view["byteOffset"]
    draco_data_end_index = draco_buffer_view["byteOffset"] + draco_data_length

    draco_data = draco_buffer[ draco_data_start_index: draco_data_end_index]
 
    # Decode the draco data
    draco_decoder = Decoder()
    
    if not draco_decoder.decode(draco_data):
        raise RuntimeError(f"{EXTENSION_NAME}: Could not decode mesh")

    # Read indices.
    index_accessor_index = gltf_primitive["indices"]
    index_accessor = gltf_data["accessors"][index_accessor_index]

    if draco_decoder.get_index_count() != index_accessor["count"]:
        # Index count of accessor and decoded index count does not match. Update the accessor.
        index_accessor.count = draco_decoder.get_index_count()
    
    if not draco_decoder.read_indices(index_accessor["componentType"]):
        raise RuntimeError(f"{EXTENSION_NAME}: Unable to decode indices.")

    index_buffer_byte_length = draco_decoder.get_index_byte_length()
    decoded_index_buffer = bytes(index_buffer_byte_length)
    draco_decoder.copy_indices(decoded_index_buffer)

    # Generate a new buffer holding the decoded index data.
    buffer_index = len( converter.buffers.keys() )
    converter.buffers[ buffer_index ] = decoded_index_buffer

    # Create a buffer view referencing the new buffer.
    buffer_view = {
        "buffer": buffer_index,
        "byteLength": index_buffer_byte_length,
        "name": f"index buffer view"
    }

    gltf_data["bufferViews"].append(buffer_view)
    buffer_view_index = len( gltf_data["bufferViews"] ) - 1

    # Update accessor to point to the new buffer view.
    index_accessor["byteOffset"] = 0
    index_accessor["bufferView"] = buffer_view_index
    gltf_data["accessors"][index_accessor_index] = index_accessor         
    
    # Read each attribute.
    for attr in extension_attributes:
        dracoId = extension_attributes[attr]
        if attr not in gltf_primitive["attributes"]:
            raise RuntimeError(f"{EXTENSION_NAME}: Draco attribute {attr} not in primitive attributes.")
        
        accessor_index = gltf_primitive["attributes"][attr]
        accessor = gltf_data["accessors"][accessor_index]
        if draco_decoder.get_vertex_count() != accessor["count"]:
            # Vertex count of accessor and decoded vertex count does not match for attribute. Update the accessor.
            accessor["count"] = draco_decoder.get_vertex_count()
            gltf_data["accessors"][accessor_index] = accessor

        if not draco_decoder.read_attribute(dracoId, accessor["componentType"], accessor["type"]):
            raise RuntimeError(f"{EXTENSION_NAME}: Could not decode attribute {attr}.")
        
        buffer_size = draco_decoder.get_attribute_byte_length(dracoId)
        decoded_buffer = bytes(buffer_size)
        draco_decoder.copy_attribute(dracoId, decoded_buffer)

        # Generate a new buffer holding the decoded vertex data.
        buffer_index = len( converter.buffers.keys() )
        converter.buffers[ buffer_index ] = decoded_buffer

        # Create a buffer view referencing the new buffer.
        buffer_view = {
            "buffer": buffer_index,
            "byteLength": buffer_size,
            "name": f"{attr} buffer view"
        }

        gltf_data["bufferViews"].append(buffer_view)
        buffer_view_index = len( gltf_data["bufferViews"] ) - 1

        # Update accessor to point to the new buffer view.
        accessor["byteOffset"] = 0
        accessor["bufferView"] = buffer_view_index
        gltf_data["accessors"][accessor_index] = accessor
