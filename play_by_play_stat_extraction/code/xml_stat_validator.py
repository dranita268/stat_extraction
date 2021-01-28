import bs4 as bs
import pandas as pd
import json
from fuzzywuzzy import process

with open('Data Models/loop_2_empty_player_agg_stats.json', 'r') as file:
    empty_player_agg_stats = json.loads(file.read())


class XMLValidator:

    def __init__(self, twogame):
        self.path = 'XML/' + ' '.join([twogame.h, "vs", twogame.v, twogame.year]).title() + '.xml'
        self.xml = open(self.path, 'r').read()
        self.soup = bs.BeautifulSoup(self.xml, 'xml')
        self.h = twogame.h
        self.h_abb = twogame.h_abb
        self.v = twogame.v
        self.v_abb = twogame.v_abb

        self.h_data = self.soup.find('team', attrs={"vh": 'H'})
        self.v_data = self.soup.find('team', attrs={"vh": 'V'})
        self.output = None


    @staticmethod
    def stat_key_correction(x, y):
        if x == 'defense':
            if y == 'int':
                x = 'pass'
            if y == 'brup':
                x, y = 'brup', 'no'
            if y == 'sacks':
                x, y = 'pass', 'sack'
            if y == 'sackyds':
                x, y = 'pass', 'sackyds'
        if x == 'rcv':
            x = 'receive'
        if x == 'fg':
            x = 'fga'
        if x == 'fumbles':
            x = 'fumble'
            if y == 'lost':
                y = 'fumblelost'
        if x == 'pass':
            if y == 'comp':
                y = 'complete'
        tup = (x, 'Reference', y)
        return tup


    def get_agg_team(self):

        layer1, layer2, layer3 = [], [], []
        for k in empty_player_agg_stats.keys():
            layer1 += [k] * len(empty_player_agg_stats.get(k).keys())
            layer2 += ['Reference'] * len(empty_player_agg_stats.get(k).keys())
            layer3 += empty_player_agg_stats.get(k)
        arrays = [layer1, layer2, layer3]
        tuples = [('player', 'player', 'name'), ('player', 'player', 'team')] + list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples)
        df = pd.DataFrame(columns=index)

        i = 0
        for t in [self.h_data, self.v_data]:
            totals = t.find('totals')
            if t.get('vh') == "H":
                team = self.h_abb
            else:
                team = self.v_abb
            df.at[i, ('player', 'player', 'team')] = team
            df.at[i, ('player', 'player', 'name')] = 'Team'
            for stat in totals.find_all():
                x = stat.name
                values = stat.attrs
                for y in values.keys():
                    tup = self.stat_key_correction(x, y)

                    try:
                        df.at[i, tup] = int(values.get(y))
                    except KeyError:
                        print(tup)
                    except ValueError:
                        pass
            i += 1

        df.set_index([('player', 'player', 'name'), ('player', 'player', 'team')], inplace=True, drop=True)
        return df


    def get_agg_player(self):
        layer1, layer2, layer3 = [], [], []
        for k in empty_player_agg_stats.keys():
            layer1 += [k] * len(empty_player_agg_stats.get(k).keys())
            layer2 += ['Reference'] * len(empty_player_agg_stats.get(k).keys())
            layer3 += empty_player_agg_stats.get(k)
        arrays = [layer1, layer2, layer3]
        tuples = [('player', 'player', 'name'), ('player', 'player', 'team')] + list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples)
        df = pd.DataFrame(columns=index)

        i = 0
        for t in [self.h_data, self.v_data]:
            if process.extractOne(t.get('name'), [self.h, self.v])[0] == self.h.lower():
                team_name = self.h_abb
            else:
                team_name = self.v_abb
            players = t.find_all('player')
            for p in players:
                player_name = p.get('checkname')
                df.at[i, ('player', 'player', 'team')] = team_name
                df.at[i, ('player', 'player', 'name')] = player_name

                for stat in p.find_all():
                    x = stat.name
                    values = stat.attrs
                    for y in values.keys():
                        tup = self.stat_key_correction(x, y)
                        # print(tup, values.get(y))
                        try:
                            df.at[i, tup] = int(values.get(y))
                        except KeyError:
                            print(tup)
                        except ValueError:
                            pass

                i += 1
        df = df.loc[df[('player', 'player', 'name')] != 'TEAM',]
        df.set_index([('player', 'player', 'name'), ('player', 'player', 'team')], inplace=True, drop=True)

        return df
