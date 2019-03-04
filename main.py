import tensorflow as tf
import gym
import numpy as np

slim = tf.contrib.slim

class QAgent():
    def __init__(self, sess, input_shape, num_actions, gamma=0.99):
        # input_shape should shape [num state history, width, height]
        # gamma is reward discount ratio
        self.sess = sess
        self.input_shape = input_shape
        self.num_actions = num_actions
        self.gamma = gamma

        self.build_prediction_network()
        self.build_target_network()
        self.build_training_operator()
    
    def build_prediction_network(self):
        with tf.variable_scope("prediction_network"):
            self.prediction_input_placeholder = tf.placeholder("float", [None] + self.input_shape)
            # slim convolution2d()
            conv1 = slim.conv2d(self.prediction_input_placeholder, num_outputs=16, kernel_size=[3, 3])
            conv2 = slim.conv2d(conv1, num_outputs=32, kernel_size=[3, 3])
            conv3 = slim.conv2d(conv2, num_outputs=64, kernel_size=[3, 3])
            flatten = slim.flatten(conv3)
            fc1 = slim.fully_connected(flatten, int(flatten.get_shape().as_list()[1] / 2))
            fc2 = slim.fully_connected(fc1, int(fc1.get_shape().as_list()[1] / 2))
            self.output = slim.fully_connected(fc2, self.num_actions, activation_fn=None)
        
    def build_target_network(self):
        with tf.variable_scope("target_network"):
            self.target_net_input_placeholder = tf.placeholder("float", [None] + self.input_shape)
            conv1 = slim.conv2d(self.target_net_input_placeholder, num_outputs=16, kernel_size=[3, 3])
            conv2 = slim.conv2d(conv1, num_outputs=32, kernel_size=[3, 3])
            conv3 = slim.conv2d(conv2, num_outputs=64, kernel_size=[3, 3])
            flatten = slim.flatten(conv3)
            fc1 = slim.fully_connected(flatten, int(flatten.get_shape().as_list()[1] / 2))
            fc2 = slim.fully_connected(fc1, int(fc1.get_shape().as_list()[1] / 2))
            self.output_target = slim.fully_connected(fc2, self.num_actions, activation_fn=None)

    def build_training_operator(self):
        with tf.variable_scope("training_operator"):
            self.q_value_placeholder = tf.placeholder("float", [None, self.num_actions])
            self.learning_rate_placeholder = tf.placeholder("float")
            self.loss = tf.reduce_mean(tf.square(self.output - self.q_value_placeholder))
            optimizer = tf.train.AdamOptimizer(learning_rate=self.learning_rate_placeholder)
            self.train_op = optimizer.minimize(self.loss)

    def predict_action(self, state):
        # Predict Q value for single state
        q = self.sess.run(self.output, feed_dict={self.prediction_input_placeholder:[state]})
        # Return index of max Q
        return np.argmax(q)
    
    def train(self, state, action, reward, state_next, tarminal, learning_rate=0.001):
        # All argument should shape like [batch, ...]

        # Get target Q value
        # Make numpy target Q array to avoid train target network
        target_q = self.sess.run(self.output_target, feed_dict={self.target_net_input_placeholder:state_next})
        target_q = np.max(target_q, axis=1)
        target_q = target_q * self.gamma + reward

        # Q is zero if terminal
        tarminal = tarminal.astype("int")
        target_q = target_q * tarminal

        feed_dict = {
            self.prediction_input_placeholder: state,
            self.q_value_placeholder: target_q,
            self.learning_rate_placeholder: learning_rate
        }

        _, loss = self.sess.run([self.train_op, self.loss], feed_dict=feed_dict)

        return loss
    
    def update_target_network(self):
        pred_net_variables = tf.global_variables(scope="prediction_network")
        target_net_variables = tf.global_variables(scope="target_network")

        if len(pred_net_variables) != len(target_net_variables):
            assert "Variable size unmatch"

        for p, t in zip(pred_net_variables, target_net_variables):
            if p.shape != t.shape:
                assert "Variable shape unmatch"
            #old_t = self.sess.run(t)
            #curr_p = self.sess.run(p)
            self.sess.run(t.assign(p))
            #curr_t = self.sess.run(t)

class EpisodeMemory():
    def __init__(self, no_discount_reward_calculation=False):
        self.states = []
        self.actions = []
        self.rewards = []
        self.states_next = []
        self.tarminals = []
        self.discounted_rewards = []

        self.no_discount_reward_calculation = no_discount_reward_calculation
    
    def reset(self):
        self.states = []
        self.actions = []
        self.rewards = []
        self.states_next = []
        self.tarminals = []
        self.discounted_rewards = []

    def add_episode(self, episode):
        self.states += episode.states
        self.actions += episode.actions
        self.rewards += episode.rewards
        self.states_next += episode.states_next
        self.tarminals += episode.tarminals
        self.discounted_rewards += episode.discounted_rewards

    def add_one_step(self, state, action, reward, state_next, tarminal):
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.states_next.append(state_next)
        self.tarminals.append(tarminal)

    def calculate_discounted_rewards(self, discount_rate=0.99):
        if self.no_discount_reward_calculation:
            assert "Wrong operation"

        self.discounted_rewards = [0 for _ in range(len(self.rewards))]
        self.discounted_rewards[-1] = self.rewards[-1]

        for i in range(len(self.rewards) - 2, -1, -1):
            self.discounted_rewards[i] = self.rewards[i] + self.discounted_rewards[i + 1] * discount_rate

