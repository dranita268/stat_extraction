import re


class KickPuntAnalyser:


    def __init__(self, twoline_obj):

        self.twoline = twoline_obj
        self.main_text = twoline_obj.text
        self.inplay_summary = []  # e.g. ['30 yard punt', '3 yard return']

        self.b_spot = ""
        self.e_spot = ""

        self.kickoff_yds = 0
        self.punt_yds = 0
        self.return_yds = 0

        self.alert = None


    @staticmethod
    def spot_minus_spot(b_spot, e_spot):
        try:
            b_side = re.search(r'[a-z]{1,3}', b_spot).group()
        except AttributeError:
            b_side = 'XX'
        b_spot_num = re.search(r'[0-9]{1,2}', b_spot).group()

        try:  # in case the spot is simply 50 without team abb in the front
            e_side = re.search(r'[a-z]{1,2}', e_spot).group()
        except AttributeError:
            e_side = 'XY'
        e_spot_num = re.search(r'[0-9]{1,2}', e_spot).group()

        if b_side == e_side:
            return abs(int(b_spot_num) - int(e_spot_num))
        else:
            return abs(100 - (int(b_spot_num) + int(e_spot_num)))


    def separate_inplay_summary(self):
        summary_template = "[0-9]{1,2}[ -]*y[ar]*ds*\.* *(?:punt|return|kick)"
        self.inplay_summary = re.findall(summary_template, self.main_text)
        for piece in self.inplay_summary:
            self.main_text = self.main_text.replace(piece, "")

        # also avoid 23 yard line (spot) being mistaken as 23 yard (yardage)
        if re.search(r'[0-9]{1,2}[- ]*y[ar]*ds*[ -]*line', self.main_text):
            self.main_text = re.sub(r"y[ar]*ds*[ -]*line", "line", self.main_text)


    def get_stats(self):

        spot_formats = [r'{} '.format(a) + r'*[0-9]{1,2}' for a in [self.twoline.game.h_abb, self.twoline.game.v_abb]]
        yards_formats = [r'[0-9]{1,2} (?:yards*|yds*)', r'(?:gain[sed]{0,2}|lost|loss) [0-9]{1,2}',
                         r'(?:for|of) [0-9]{1,2}']
        b_spot = self.b_spot
        if self.twoline.ParentName == 'PuntReturn':  # punt yards and return yards both needed
            b_spot = ''.join(self.twoline.parsed_beginning_context[3:5])
            spots = [s.group() for s in re.finditer('|'.join(spot_formats), self.main_text)]
            yards = [int(re.sub(r'y[ar]*ds*\.*', '', y.group()).strip()) for y in
                     re.finditer('|'.join(yards_formats), self.main_text)]

            if len(spots) == 2:  # Punt to spot, return to spot
                punt_to, return_to = spots
                self.punt_yds = self.spot_minus_spot(b_spot, punt_to)
                self.return_yds = self.spot_minus_spot(punt_to, return_to)

            else:
                if len(yards) == 2:  # punt for x yards, return y yards
                    self.punt_yds, self.return_yds = yards

        if self.twoline.ParentName in ['PuntDowned', 'PuntFC', 'PuntOOB', 'PuntTB',
                                       'PuntBlocked']:  # only punt yards needed
            b_spot = ''.join(self.twoline.parsed_beginning_context[3:5])
            spot_formats = [r'{} '.format(a) + r'*[0-9]{1,2}' for a in
                            [self.twoline.game.h_abb, self.twoline.game.v_abb]]
            spots = [s.group() for s in re.finditer('|'.join(spot_formats), self.main_text)]
            if self.twoline.ParentName == 'PuntTB' and len(spots) == 0:
                spots.append([t for t in self.twoline.game.team_abbreviations if t != self.twoline.poss][0] + '0')
            if len(spots) == 1:
                e_spot = spots[0]
                self.punt_yds = self.spot_minus_spot(b_spot, e_spot)

        if self.twoline.ParentName == 'KickoffTB':  # kick off into the endzone from 35 yard line in total 65 yards
            self.kickoff_yds = 65

        if self.twoline.ParentName == 'KickoffReturn':  # according to rules: kickoff is always from 35 yard line
            b_spot = self.twoline.poss + '35'
            if any(['SAF' in str(pn) for pn in self.twoline.game.game_df.loc[self.twoline.index - 4:self.twoline.index, 'ParentName']]):
                # ko after safety is from 20 yards line
                b_spot = self.twoline.poss + '20'

            spots = [s.group() for s in re.finditer('|'.join(spot_formats), self.main_text)]
            yards = [int(re.sub(r'y[ar]*ds*\.*', '', y.group()).strip()) for y in
                     re.finditer('|'.join(yards_formats), self.main_text)]

            if len(spots) == 2:
                kickoff_to, return_to = spots
                self.kickoff_yds = self.spot_minus_spot(b_spot, kickoff_to)
                self.return_yds = self.spot_minus_spot(kickoff_to, return_to)

            elif len(yards) == 2:
                self.kickoff_yds, self.return_yds = yards

        # if there is a summary and yards can't be calculated, use the summary
        if any([self.kickoff_yds == 0 and self.punt_yds == 0, self.return_yds == 0]) and self.inplay_summary != []:
            for piece in self.inplay_summary:
                yds_num = int(re.search('[0-9]{1,2}',piece).group())
                if re.search('punt', piece):
                    self.punt_yds = yds_num
                elif re.search('kick', piece) and 'kickoff' in self.twoline.ParentName:
                    self.kickoff_yds = yds_num
                elif re.search('return', piece):
                    self.return_yds = yds_num
        self.b_spot = b_spot


    def context_validation_for_return_plays(self, parsed_supv_context):
        spot_formats = [r'{} '.format(a) + r'*[0-9]{1,2}' for a in [self.twoline.game.h_abb, self.twoline.game.v_abb]]
        yards_formats = [r'[0-9]{1,2} (?:yards*|yds*)', r'(?:gain[sed]{0,2}|lost|loss) [0-9]{1,2}',
                         r'(?:for|of) [0-9]{1,2}']

        if self.twoline.ParentName in ['PuntReturn', 'KickoffReturn']:
            # b_spot = ''.join(self.twoline.parsed_beginning_context[3:5])
            self.e_spot = ''.join(parsed_supv_context[3:5])
            try:
                net_yards = self.spot_minus_spot(self.b_spot, self.e_spot)  # should equal to punt/kickoff yards - return yards
            except:
                return

            if abs(net_yards) != abs(self.kickoff_yds + self.punt_yds - self.return_yds) and \
                   self.b_spot != "" and self.e_spot != "":
                # if one of the two needed yards is 0, calculate using net yards
                if self.kickoff_yds == self.punt_yds == 0 and self.return_yds != 0:
                    if 'Punt' in self.twoline.ParentName:
                        self.punt_yds = self.return_yds + net_yards
                    elif 'Kickoff' in self.twoline.ParentName:
                        self.kickoff_yds = self.return_yds + net_yards
                elif self.return_yds == 0 and not any([self.kickoff_yds == 0, self.punt_yds == 0]):
                    self.return_yds = self.kickoff_yds+self.punt_yds-net_yards
                else:  # if action and return yards both exist but still don't agree, or if they are both zero
                    result_position = re.search(r'ret[urn]*|r[au]ns* *back', self.main_text).span()[0]

                    if len(re.findall(r'\b[0-9]{1,2} *(?:yds\.*|yards*)\b', self.main_text[result_position:])) == 1:
                        return_yards = re.search(r'[0-9]{1,2} *(?:yds\.*|yards*)*',
                                                 self.main_text[result_position:]).group()
                        self.return_yds = int(re.search(r'[0-9]{1,2}', return_yards).group())
                        action_yards = net_yards + self.return_yds
                        if 'Punt' in self.twoline.ParentName:
                            self.punt_yds = action_yards
                        elif 'Kickoff' in self.twoline.ParentName:
                            self.kickoff_yds = action_yards

            # re-check
            if abs(net_yards) == abs(self.kickoff_yds + self.punt_yds - self.return_yds):
                self.alert = 'reverse validation successful'
            else:
                self.alert = 'still have problem'
