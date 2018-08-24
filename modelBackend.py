import gc

from utils import *
from vgg19 import Vgg19

def model(content_path, style_path, alpha, beta, lambdas, num_iterations, initial_learning_rate, learning_rate_decay):
    tf.reset_default_graph()
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    # Read the content and style images and create a noisy version of the content image to be the target_image
    content_means, content_variances, content_image = readAndNormalize(content_path)
    style_means, style_variances, style_image = readAndNormalize(style_path)

    means = (alpha * content_means + beta * style_means) / (alpha + beta)
    variances = (alpha * content_variances + beta * style_variances) / (alpha + beta)

    # Add another dimension to the images because that's what the model needs
    content_image = content_image[np.newaxis, ...].astype(dtype=np.float32)
    style_image = style_image[np.newaxis, ...].astype(dtype=np.float32)
    target_means, target_variances, target_image = addGausianNoise(content_image[0, :, :, :])

    content_model = Vgg19()
    style_model = Vgg19()
    target_model = Vgg19()

    style_activations = dict()
    target_style_activations = dict()
    layer_costs = dict()

    target_image_variable = tf.get_variable(name='target_activation', dtype=tf.float32, initializer=target_image)
    content_model.build(content_image)
    content_activation = content_model.conv3_1
    style_model.build(style_image)
    style_activations['conv2_1'] = style_model.conv2_1
    style_activations['conv2_2'] = style_model.conv2_2
    style_activations['conv3_1'] = style_model.conv3_1
    style_activations['conv3_2'] = style_model.conv3_2
    target_model.build(target_image_variable)
    target_content_activation = target_model.conv3_1
    target_style_activations['conv2_1'] = target_model.conv2_1
    target_style_activations['conv2_2'] = target_model.conv2_2
    target_style_activations['conv3_1'] = target_model.conv3_1
    target_style_activations['conv3_2'] = target_model.conv3_2
    content_cost = contentCost(content_activation, target_content_activation)
    style_cost = styleCost(style_activations, target_style_activations, lambdas)
    total_cost = totalCost(content_cost, style_cost, alpha, beta)

    learning_rate = tf.placeholder(name='learning_rate', dtype=tf.float32)
    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
    train_step = optimizer.minimize(total_cost)

    with tf.Session(config=config) as session:

        session.run(tf.global_variables_initializer())
        for iteration in range(num_iterations):

            session.run(train_step,
                        feed_dict={learning_rate: initial_learning_rate / (1 + learning_rate_decay * iteration)})
            if iteration % 10 == 0:
                current_content_cost, current_style_cost = session.run([content_cost, style_cost])
                print("Iteration number {}: {} ~ 10^{}  <--->  {} ~ 10^{} ".format(iteration, current_content_cost,
                                                                                   np.floor(
                                                                                       np.log10(current_content_cost)),
                                                                                   current_style_cost, np.floor(
                        np.log10(current_style_cost))))

        output, final_style_cost, final_content_cost = session.run([target_image_variable, style_cost, content_cost])
        output = output[0, :, :, :] * content_variances + content_means
        content_path = content_path[:-4]
        content_path = content_path[17:]
        style_path = style_path[:-4]
        style_path = style_path[15:]
        name = 'generated images/{}+{}.jpg'.format(content_path, style_path)
        cv2.imwrite(name, output)
        print(name + " was created. Final content cost was {}; Final style cost was {}.".format(final_content_cost,
                                                                                                final_style_cost))
        session.close()
        gc.collect()
