import gym
from gym.spaces import Discrete, Box
from gym.utils import seeding
from gym_gopherfx.envs.data.reader import Reader


class GopherfxV1Env(gym.Env):
    metadata = {'render.modes': ['human']}
    multiplier = 100
    action_investment = 1

    def __init__(self, data_folder='data/candlerates/EUR_USD/2018-06/'):
        self.observation_space = Box(low=0, high=1000, shape=(1,))
        self.action_space = Discrete(3)
        self.open_contracts = {'ask': [], 'bid': []}
        self.elapsed = 0
        self.episode = 0
        self.budget = 100
        self.sell_info = None

        self.last_action = None
        self.last_reward = None

        self.data = Reader.readjson(data_folder)
        self.max_episodes = len(self.data)
        self.episode_length = self.get_episode_length()

    def re_init(self, data_folder='data/candlerates/EUR_USD/2018-06/'):
        self.data = Reader.readjson(data_folder)
        self.max_episodes = len(self.data)
        self.episode_length = self.get_episode_length()

    def step(self, action):
        self.last_action = action
        self.sell_info = {}

        observation = self.get_raw_observation()

        reward = 0
        if action == 0:
            pass
        elif action == 1:
            contract = {'investment': self.action_investment * self.multiplier,
                        'observation': observation,
                        'invested_at': self.elapsed}

            action_code = 'ask'
            complementary_action_code = 'bid'
            reward = self.execute_contract(action_code, complementary_action_code, contract)

        elif action == 2:
            contract = {'investment': - self.action_investment * self.multiplier,
                        'observation': observation,
                        'invested_at': self.elapsed}
            action_code = 'bid'
            complementary_action_code = 'ask'
            reward = self.execute_contract(action_code, complementary_action_code, contract)

        self.elapsed += 1
        done = 0
        if self.elapsed > self.episode_length - 1:
            done = 1
            self.reset_episode()
        elif self.budget <= 0:
            done = 1
            self.reset_episode()
            reward = -1

        self.last_reward = reward

        return self.get_observation(), reward, done, {}

    def execute_contract(self, action_code, complementary_action_code, contract):
        reward = 0

        if len(self.open_contracts[complementary_action_code]):
            reward = self.get_contract_value(self.get_raw_observation()[0])
            start_contract = self.open_contracts[complementary_action_code].pop(0)
            self.budget += reward
            if action_code == 'bid':
                self.sell_info = tuple(
                    [start_contract['observation'][0]['time'], contract['observation'][0]['time'],
                     reward,
                     start_contract['observation'][0][complementary_action_code]['c'],
                     contract['observation'][0][action_code]['c'], self.elapsed - start_contract['invested_at'],
                     action_code,
                     self.budget])
            else:
                self.sell_info = tuple(
                    [contract['observation'][0]['time'], start_contract['observation'][0]['time'],
                     reward,
                     contract['observation'][0][action_code]['c'],
                     start_contract['observation'][0][complementary_action_code]['c'],
                     self.elapsed - start_contract['invested_at'], action_code,
                     self.budget])
        else:
            self.open_contracts[action_code].append(contract)
        return reward

    def get_observation(self):
        data = self.get_episode_data()
        current = data[self.elapsed]
        observation = tuple([
            current['volume'],
            current['time'],
            current['bid']['o'],
            current['bid']['h'],
            current['bid']['l'],
            current['bid']['c'],
            current['ask']['o'],
            current['ask']['h'],
            current['ask']['l'],
            current['ask']['c'],
            self.get_contract_value(current),
            self.get_contract_close_action_type()
        ])
        return observation

    def get_contract_value(self, current_observation):
        contract_value = 0.0
        action_code = False
        if len(self.open_contracts['bid']):
            start_contract = self.open_contracts['bid'][0]
            action_code = 'ask'
            complementary_action_code = 'bid'
        if len(self.open_contracts['ask']):
            start_contract = self.open_contracts['ask'][0]
            action_code = 'bid'
            complementary_action_code = 'ask'

        if action_code:
            contract_value = start_contract['investment'] * (
                    float(current_observation[action_code]['c'])
                    - float(start_contract['observation'][0][complementary_action_code]['c']))
        return contract_value

    def get_contract_close_action_type(self):
        close_action_type = 0
        if len(self.open_contracts['bid']):
            close_action_type = 1
        if len(self.open_contracts['ask']):
            close_action_type = 2

        return close_action_type

    def get_raw_observation(self):
        data = self.get_episode_data()
        observation = tuple([data[self.elapsed]])
        return observation

    def reset_episode(self):
        self.open_contracts = {'ask': [], 'bid': []}
        self.budget = 100
        self.episode += 1
        self.elapsed = 0
        self.episode_length = self.get_episode_length()
        if self.episode > self.max_episodes:
            self.reset()

    def get_episode_length(self):
        return len(self.get_episode_data())

    def reset(self):
        self.open_contracts = {'ask': [], 'bid': []}
        self.budget = 100
        self.episode = 0
        self.elapsed = 0
        self.episode_length = self.get_episode_length()

    def render(self, mode='human', close=False):
        # output = "Action " + str(self.last_action) + ", reward " + str(self.last_reward) + " observation %s" % (
        #     self.get_observation(),)
        output = ""
        if self.sell_info:
            output = self.sell_info

        return output

    def _seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def get_episode_data(self):
        return self.data[self.episode % self.max_episodes]['rates']

    def get_episode_name(self):
        return self.data[self.episode % self.max_episodes]['name']

    def _step(self, action):
        pass

    def _reset(self):
        pass
