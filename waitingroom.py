def group_by_arrival_time_method(subsession: Subsession, waiting_players):
    import time
    PLAYERS_PER_GROUP = 5
    now = time.time()
    
    competition_players = [p for p in waiting_players if p.competition]
    
    if len(competition_players) >= PLAYERS_PER_GROUP:
        return competition_players[:PLAYERS_PER_GROUP]
    
    for p in competition_players:
        if 'arrival_time' not in p.participant.vars:
            p.participant.vars['arrival_time'] = now
    
    for p in competition_players:
        waited = now - p.participant.vars['arrival_time']
        if waited > 60:
            for late_p in competition_players:
                late_p.participant.vars['grouping_failed'] = True
                late_p.participant.vars['timeout_message'] = "⏰ Not enough players joined your group within the time limit."
            print(f"⚠️ Timeout: Only {len(competition_players)} players — marking as failed.")
            return competition_players  # return the players as a FLAT list!
    
    return None  # Keep waiting


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



page_sequence = [GroupWait_Start, IntroductionPage, ExplorationPhase, TrasitionPage, PeformancePhase, ResultPage]
