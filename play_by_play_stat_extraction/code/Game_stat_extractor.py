import os
try:
    from step1_objects import OneGame, OneLine
    from step2_objects import TwoGame, TwoLine
except:
    os.system('python3 step1_data_model.py')
    os.system('python3 step2_data_model.py')
    from step1_objects import OneGame, OneLine
    from step2_objects import TwoGame, TwoLine


class StatExtractor:

    def __init__(self, h, v, year):
        self.h = h
        self.v = v
        self.year = year
        self.onegame = None
        self.twogame = None


    def extract_stats(self):
        h, v, year = self.h, self.v, self.year
        self.onegame = OneGame(h, v, year)
        self.onegame.analyse_game()
        print("")
        self.twogame = TwoGame(h, v, year)
        self.twogame.extract_game_stats()
        print("")


# if __name__ == "__main__":
#     extractor = StatExtractor('Alabama', 'Kentucky', 1972)
#     extractor.extract_stats()


# ------------------------------------------------------------
# 6th round of testing: BA template review
# games = [StatExtractor('Alabama','Ole Miss',1970),
#             StatExtractor('Alabama','Mississippi State',1998),
#             StatExtractor('Purdue','notre dame',1980),
#             StatExtractor('Purdue','Ohio State',1988),
#             StatExtractor('Alabama','Kentucky',1972),
#             StatExtractor('Alabama','Houston',1971),
#             StatExtractor('Alabama','Virginia Tech',1968)
#             ]
# for game in games:
#     game.extract_stats()


# ------------------------------------------------------------
# 7th round of testing: BA template review
# games = [StatExtractor('TAMU', 'Lousiana Tech', '1996'),
#          StatExtractor('Alabama', 'LSU', '1980'),
#          StatExtractor('Alabama', 'Auburn', '1996'),
#          StatExtractor('TAMU', 'Colorado', '1995'),
#          StatExtractor('TAMU', 'Missouri', '1998'),
#          StatExtractor('TAMU', 'Oklahoma', '1999'),
#          StatExtractor('Alabama', 'Tennessee', '1995'),
#          StatExtractor('TAMU', 'Nebraska', '1999'),
#          StatExtractor('TAMU', 'Texas', '1999'),
#          StatExtractor('TAMU', 'Texas', '1998'),
#          StatExtractor('Tamu', 'Alabama', '1968'),
#          StatExtractor('TAMU', 'North Texas', '1996'),
#          StatExtractor('Alabama', 'Mississippi', '1970'),
#          StatExtractor('Alabama', 'Mississippi', '1998'),
#          StatExtractor('TAMU', 'Oklahoma', '1996')
#          ]
# for game in games:
#     game.extract_stats()
