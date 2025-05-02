def group_by_arrival_time_method(subsession: Subsession, waiting_players):
    import time
    PLAYERS_PER_GROUP = C.PLAYERS_PER_GROUP
    now = time.time()
    
    # Filter players eiligble for this wait page
    competition_players = [p for p in waiting_players if p.competition]
    
    # Group players by both competition and time pressure
    treatment_groups = {}
    for p in competition_players:
        key = (p.competition, p.time_pressure) # competition is always true here
        treatment_groups.setdefault(key, []).append(p)
        
    # Form groups or check timeout 
    for (competition, time_pressure), players in treatment_groups.items():
        for p in players:
            p.participant.vars.setdefault('arrival_time', now)
            
        if len(players) >= PLAYERS_PER_GROUP:
           return players[:PLAYERS_PER_GROUP]
            
        for p in players: 
            waited = now - p.participant.vars['arrival_time']
            if waited > 60:
                for late_p in competition_players:
                    late_p.participant.vars['grouping_failed'] = True
                    late_p.participant.vars['timeout_message'] = "Not enough players joined your group within the time limit."
                print(f" Timeout: Only {len(competition_players)} players — marking as failed.")
                return competition_players  # return the players as a FLAT list!
    return None

class Group(BaseGroup):
    pass
def after_all_player_arrive(group: Group): ## also commented out for testing
    for p in group.get_players():
            if p.participant.vars.get('grouping_failed'):
                p.participant.vars['timeout_message'] = (
                    "Not enough players joined your group within the time limit."
                )


# WaitPage
class GroupWait_Start(WaitPage):
    group_by_arrival_time = True
    after_all_players_arrive = after_all_player_arrive
    @staticmethod
    def is_displayed(player: Player):
        return player.competition  # only competition players wait here

class WaitTrainning_Explore(WaitPage):
    after_all_players_arrive = after_all_player_arrive
    @staticmethod
    def is_displayed(player: Player):
        return player.competition  # only competition players wait here

class WaitTrainning_Perform(WaitPage):
    after_all_players_arrive = after_all_player_arrive
    @staticmethod
    def is_displayed(player: Player):
        return player.competition  # only competition players wait here

class WaitExplore(WaitPage):
    after_all_players_arrive = after_all_player_arrive
    @staticmethod
    def is_displayed(player: Player):
        return player.competition  # only competition players wait here

class WaitPerform(WaitPage):
    after_all_players_arrive = after_all_player_arrive
    @staticmethod
    def is_displayed(player: Player):
        return player.competition  # only competition players wait here

page_sequence = [GroupWait_Start, IntroductionPage, 
                 WaitTrainning_Explore, TrainingExplore, WaitTraining_Perform, TrainingPerform,
                 WaitExplore,ExplorationPhase, WaitPerform, TrasitionPage, PeformancePhase, ResultPage]
