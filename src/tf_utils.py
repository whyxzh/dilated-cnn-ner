from __future__ import division
import tensorflow as tf
import numpy as np

eps = 1e-5


def gather_nd(params, indices, shape=None, name=None):
    if shape is None:
        shape = params.get_shape().as_list()
    rank = len(shape)
    flat_params = tf.reshape(params, [-1])
    multipliers = [reduce(lambda x, y: x * y, shape[i + 1:], 1) for i in range(0, rank)]
    indices_unpacked = tf.unpack(tf.cast(tf.transpose(indices, [rank - 1] + range(0, rank - 1), name), 'int32'))
    flat_indices = sum([a * b for a, b in zip(multipliers, indices_unpacked)])
    return tf.gather(flat_params, flat_indices, name=name)


def repeat(tensor, reps):
    flat_tensor = tf.reshape(tensor, [-1, 1])  # Convert to a len(yp) x 1 matrix.
    repeated = tf.tile(flat_tensor, [1, reps])  # Create multiple columns.
    repeated_flat = tf.reshape(repeated, [-1])  # Convert back to a vector.
    return repeated_flat


# def repeat_elements(x, rep, axis, axis_size):
#     '''Repeats the elements of a tensor along an axis, like np.repeat
#     If x has shape (s1, s2, s3) and axis=1, the output
#     will have shape (s1, s2 * rep, s3)
#     This function is taken from keras backend
#     '''
#     # x_shape = x.get_shape().as_list()
#     # splits = tf.split(axis, x_shape[axis], x)
#     splits = tf.unpack(x, axis=axis)
#     x_rep = [s for s in splits for i in range(rep)]
#     return tf.concat(axis, x_rep)

def last_relevant(output, length):
    batch_size = tf.shape(output)[0]
    max_length = tf.shape(output)[1]
    out_size = int(output.get_shape()[2])
    index = tf.range(0, batch_size) * max_length + (length - 1)
    flat = tf.reshape(output, [-1, out_size])
    relevant = tf.gather(flat, index)
    return relevant


def apply_nonlinearity(parameters, nonlinearity_type):
    if nonlinearity_type == "relu":
        return tf.nn.relu(parameters, name="relu")
    elif nonlinearity_type == "tanh":
        return tf.nn.tanh(parameters, name="tanh")
    elif nonlinearity_type == "sigmoid":
        return tf.nn.sigmoid(parameters, name="sigmoid")


def embedding_values(shape, old=False):
    if old:
        embeddings = np.multiply(np.add(np.random.rand(shape[0], shape[1]).astype('float32'), -0.1), 0.01)
    else:
        # xavier init
        drange = np.sqrt(6.0 / (np.sum(shape)))
        embeddings = drange * np.random.uniform(low=-1.0, high=1.0, size=shape).astype('float32')
    return embeddings


def initialize_embeddings(shape, name, pretrained=None, old=False):
    zero_pad = tf.constant(0.0, dtype=tf.float32, shape=[1, shape[1]])
    if pretrained is None:
        embeddings = embedding_values(shape, old)
    else:
        embeddings = pretrained
    return tf.concat(0, [zero_pad, tf.get_variable(name=name, initializer=embeddings)])


def initialize_weights(shape, name, init_type, gain="1.0", divisor=1.0):
    if init_type == "random":
        return tf.get_variable(name, initializer=tf.truncated_normal(shape, stddev=0.1))
    if init_type == "xavier":
        # shape_is_tensor = issubclass(type(shape), tf.Tensor)
        # rank = len(shape.get_shape()) if shape_is_tensor else len(shape)
        # if rank == 4:
        #     return tf.get_variable(name, shape=shape, initializer=tf.contrib.layers.xavier_initializer_conv2d())
        return tf.get_variable(name, shape=shape, initializer=tf.contrib.layers.xavier_initializer())
    if init_type == "identity":
        # todo whelp this is definitely wrong for 2d matrices
        middle0 = int(shape[0] / 2)
        middle1 = int(shape[1] / 2)
        if shape[2] == shape[3]:
            array = np.zeros(shape, dtype='float32')
            identity = np.eye(shape[2], shape[3])
            array[middle0, middle1] = identity
        else:
            m1 = divisor / shape[2]
            m2 = divisor / shape[3]
            sigma = eps*m2
            array = np.random.normal(loc=0, scale=sigma, size=shape).astype('float32')
            for i in range(shape[2]):
                for j in range(shape[3]):
                    if int(i*m1) == int(j*m2):
                        array[middle0, middle1, i, j] = m2
        return tf.get_variable(name, initializer=array)
    if init_type == "varscale":
        return tf.get_variable(name, shape=shape, initializer=tf.contrib.layers.variance_scaling_initializer())
    if init_type == "orthogonal":
        gain = np.sqrt(2) if gain == "relu" else 1.0
        array = np.zeros(shape, dtype='float32')
        random = np.random.normal(0.0, 1.0, (shape[2], shape[3])).astype('float32')
        u, _, v_t = np.linalg.svd(random, full_matrices=False)
        middle = int(shape[1] / 2)
        array[0, middle] = gain * v_t
        return tf.get_variable(name, initializer=array)


def residual_layer(input, w, b, dilation, nonlinearity, batch_norm, name, batch_size, max_sequence_len, activation, training):
    # if activation == "pre" (2): BN -> relu -> weight -> BN -> relu -> weight -> addition
    conv_in_bn = tf.contrib.layers.batch_norm(input, decay=0.995, scale=False, is_training=training, trainable=True) \
                    if batch_norm and activation == 2 else input
    conv_in = apply_nonlinearity(conv_in_bn, nonlinearity) if activation == 2 else conv_in_bn
    conv = tf.nn.atrous_conv2d(
        conv_in,
        w,
        rate=dilation,
        padding="SAME",
        name=name)
    conv_b = tf.nn.bias_add(conv, b)

    # if activation == "post" (1): weight -> BN -> relu -> weight -> BN -> addition -> relu
    conv_out_bn = tf.contrib.layers.batch_norm(conv_b, decay=0.995, scale=False, is_training=training, trainable=True) \
                    if batch_norm and activation != 2 else conv_b
    conv_out = apply_nonlinearity(conv_out_bn, nonlinearity) if activation != 2 else conv_out_bn

    # if activation == "none" (0): weight -> BN -> relu
    conv_shape = w.get_shape()
    if conv_shape[-1] != conv_shape[-2] and activation != 0:
        # if len(input_shape) != 2:
        input = tf.reshape(input, [-1, tf.to_int32(conv_shape[-2])])
        w_r = initialize_weights([conv_shape[-2], conv_shape[-1]], "w_o_" + name, init_type="xavier")
        b_r = tf.get_variable("b_r_" + name, initializer=tf.constant(0.01, shape=[conv_shape[-1]]))
        input_projected = tf.nn.xw_plus_b(input, w_r, b_r, name="proj_r_" + name)
        # if len(output_shape) != 2:
        input_projected = tf.reshape(input_projected, tf.pack([batch_size, 1, max_sequence_len, tf.to_int32(conv_shape[-1])]))
        return tf.add(input_projected, conv_out)
    else:
        return conv_out


# def residual_layer(input, output, input_size, output_size, nonlinearity, name):
#     output_projected = apply_nonlinearity(output, nonlinearity)
#     if input_size != output_size:
#         w_r = initialize_weights([input_size, output_size], "w_o_" + name, init_type="xavier")
#         b_r = tf.get_variable("b_r_" + name, initializer=tf.constant(0.01, shape=[output_size]))
#         input_projected = tf.nn.xw_plus_b(input, w_r, b_r, name="proj_r_" + name)
#     else:
#         input_projected = input
#     return tf.add(input_projected, output_projected)