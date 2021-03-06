import tensorflow as tf
import src.sparseae as sparseae
import src.utils as utils

import os
import argparse

def argumentparser():
    parser = argparse.ArgumentParser(description='Train an SparseAE')
    parser.add_argument('--batch_size', type=int, default=50,
                        help='Batch size...')
    parser.add_argument('--epochs', type=int, default=50,
                        help='number of epochs')
    parser.add_argument('--logdir', type=str, default='/tmp/sparseae/',
                        help='location to save logs')
    parser.add_argument('--n_hidden', type=int, default=12)
    parser.add_argument('--width', type=int, default=16)
    parser.add_argument('--depth', type=int, default=4)
    parser.add_argument('--learning_rate', type=float, default=0.0001)
    parser.add_argument('--beta', type=float, default=1.0)
    return parser.parse_args()

def main(args):
    from tensorflow.examples.tutorials.mnist import input_data
    mnist = input_data.read_data_sets("/tmp/MNIST_data/", one_hot=True)

    PL = utils.PyramidLoss(32, 3)

    with tf.variable_scope('s'):
        nn = sparseae.SparseAE(args.n_hidden, args.width, args.depth)

        x = tf.placeholder(shape=[None, 32, 32, 1], dtype=tf.float32)
        recon_loss, latent_loss = nn.make_losses(x)
        pl_loss = PL((x, nn.y))
        loss = pl_loss+args.beta*latent_loss

    train_summaries = [
        tf.summary.scalar('train/loss/recon', recon_loss),
        tf.summary.scalar('train/loss/latent', latent_loss),
        tf.summary.histogram('latents', nn.z),
        tf.summary.image('train/input', x),
        tf.summary.image('train/recon', tf.nn.sigmoid(nn.y)),
        # tf.summary.scalar('train/Px/real', p_real),
        # tf.summary.scalar('train/Px/fake', p_fake)
    ]

    p_real = nn.estimate_density(x)
    p_fake = nn.estimate_density(tf.random_normal(shape=tf.shape(x)))
    test_summaries = [
        tf.summary.scalar('test/loss/recon', recon_loss),
        tf.summary.scalar('test/loss/latent', latent_loss),
        tf.summary.image('test/input', x),
        tf.summary.image('test/recon', tf.nn.sigmoid(nn.y)),
        tf.summary.scalar('test/Px/real', tf.reduce_mean(p_real)),
        tf.summary.scalar('test/Px/fake', tf.reduce_mean(p_fake))
    ]

    train_merged = tf.summary.merge(train_summaries)
    test_merged = tf.summary.merge(test_summaries)

    global_step = tf.train.get_or_create_global_step()
    learning_rate = args.learning_rate

    opt = tf.train.AdamOptimizer(learning_rate)
    gnvs = opt.compute_gradients(loss, var_list=nn.encoder.variables+nn.decoder.variables)
    # gnvs = [(tf.clip_by_norm(g, 1), v) for g, v in gnvs]
    train_step = opt.apply_gradients(gnvs, global_step=global_step)
    saver = tf.train.Saver()
    checkpoint = tf.contrib.eager.Checkpoint(**{var.name: var for var in tf.global_variables()})


    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        writer = tf.summary.FileWriter(args.logdir, sess.graph)

        for i in range(args.epochs*1000):
            batch_x, _ = mnist.train.next_batch(args.batch_size)
            _, train_summ = sess.run([train_step, train_merged],
                                     feed_dict={x: sparseae.SparseAE.preprocess(batch_x)})

            if i % 10 == 0:
                writer.add_summary(train_summ, i)

            if i % 100 == 0:
                L, test_summ = sess.run([loss, test_merged],
                                                    feed_dict={x:
                            sparseae.SparseAE.preprocess(mnist.test.images[:100, ...])})
                print('\rStep: {} Loss: {}'.format(i, L), end='', flush=True)
                writer.add_summary(test_summ, i)

            if i % 1000 == 0:
                save_path = checkpoint.save(os.path.join(args.logdir, "infovae_ckpt.ckpt"))
                save_path = saver.save(sess, os.path.join(args.logdir,"infovae_saver.ckpt"))
                print(save_path)

if __name__ == '__main__':
    main(argumentparser())
