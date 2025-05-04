
from otree.api import *
c = cu

doc = 'pilot\npre-decisional search\ntime pressure & competition'
class C(BaseConstants):
    NAME_IN_URL = 'sampling_game_pilot'
    PLAYERS_PER_GROUP = 5
    NUM_ROUNDS = 1
    NUM_BLOCKS = 10
    NUM_TRIALS = 50
    TOTAL_TRIAL = 50
    BLOCK_SIZE = 10
    REWARDS = (100, 100, 50, 50)
    ENDOWMENT = cu(3000)
    TRAINING_REWARDS = (100, 10, 30, 20)
    TRAINING_COSTS = (0, 10, 0, 0)
class Subsession(BaseSubsession):
    my_field = models.FloatField()
def generate_block(subsession: Subsession):
    import random
    costs = [[150, 200, 250, 300, 350], # Deck A
             [1250], # Deck B
             [50, 50, 50, 50, 50], # Deck C
             [250]] #Deck D
    for ele in costs:
    # add zeroes until it has 10 elements
        ele += [0] * (C.BLOCK_SIZE - len(ele))
        random.shuffle(ele)
    return costs
def creating_session(subsession: Subsession):
    session = subsession.session
    import itertools
    import random
    
    session = subsession.session
    
    # === Generate session-level IOWA costs ===
    costs = [[], [], [], []]
    for _ in range(C.NUM_BLOCKS):
        block = generate_block(subsession)  # block = [deck_A, deck_B, deck_C, deck_D]
        for i in range(4):
            costs[i] += block[i]
    session.vars['iowa_costs'] = costs
    
    # === Generate all treatment combinations (2x2) ===
    treatment_combinations = list(itertools.product([True, False], [True, False]))
    
    players = subsession.get_players()
    repeated_combinations = list(itertools.islice(itertools.cycle(treatment_combinations), len(players)))
    random.shuffle(repeated_combinations)
    
    # === Assign treatments to players ===
    for player, (time_pressure, competition) in zip(players, repeated_combinations):
        player.time_pressure = time_pressure
        player.competition = competition
    
        deck_layout = ['A', 'B', 'C', 'D']
        random.shuffle(deck_layout) 
        # Randomized deck layout
        player.deck_layout = ''.join(deck_layout)
    
        print(f"Player {player.id_in_subsession}: TP={time_pressure}, COMP={competition}, Deck={player.deck_layout}")
class Group(BaseGroup):
    pass
class Player(BasePlayer):
    num0 = models.IntegerField(initial=0)
    num1 = models.IntegerField(initial=0)
    num2 = models.IntegerField(initial=0)
    num3 = models.IntegerField(initial=0)
    num_trials = models.IntegerField(initial=0)
    deck_layout = models.StringField()
    time_pressure = models.BooleanField()
    competition = models.BooleanField()
    in_training = models.BooleanField(initial=True)
    training_exploration = models.BooleanField(initial=True)
    in_exploration_phase = models.BooleanField(initial=False)
    start_time = models.FloatField()
    end_time = models.FloatField()
    training_start_time = models.FloatField()
    exploration_duration = models.FloatField(initial=0)
    penalty = models.FloatField(initial=0)
    cum_payoff = models.FloatField(initial=0)
    performance_starting_payoff = models.FloatField()
    exploration_log = models.LongStringField()
    performance_log = models.LongStringField()
    best_deck_selection = models.StringField(initial='choice = ["A", "B", "C", "D"]')
    cum_payoff_training = models.FloatField(initial=0)
    exploration_temp_log = models.LongStringField(initial='[]')
    training_passed = models.BooleanField(initial=True)
    training_exploration_duration = models.FloatField()
    training_penalty = models.FloatField(initial=0)
    training_cum_payoff = models.FloatField(initial=0)
    training_duration = models.FloatField()
    training_performance_start = models.FloatField()
    training_payoff = models.FloatField()
def get_penalty(player: Player):
    # Calculate penlaty when time pressure is true
    if player.time_pressure:
        if player.in_training:
            duration = player.training_exploration_duration if player.training_exploration_duration is not None else 0
        else:
            duration = player.exploration_duration if player.exploration_duration is not None else 0
        return round(50 * duration)
    else: 
        print("Time pressure is False. Returning 0.")
        return 0
def live_method(player: Player, data):
    session = player.session
    group = player.group
    participant = player.participant
    import time
    import json
    
    my_id = player.id_in_group
    print(f"[LIVE] Player {my_id} sent data: {data}")
    print(f"[DEBUG] live_method triggered — "
          f"in_training={player.in_training}, "
          f"training_exploration={player.training_exploration}, "
          f"in_exploration_phase={player.in_exploration_phase}, "
          f"data={data}")
    
    # === TRAINING PHASE ===
    if player.in_training:
        if data.get('start_training'):
            start_training(player)
            return {my_id: dict(training=True, training_duration=0.0)}
        # Wait for participant to read the instructions before they start the training
        if player.field_maybe_none('training_start_time') is None:
            print(f"[LIVE] Player {my_id} has not started training yet. Waiting for start.")
            return {my_id: dict(training=True, waiting_for_start=True)}
    
        training_duration = time.time() - player.training_start_time
    
        # Training exploration phase: 
        if player.training_exploration:
            # Record training duraction and exploration duration 
            player.training_exploration_duration = training_duration
            player.training_penalty = get_penalty(player)
            player.training_cum_payoff = 3000 - player.training_penalty
            print(f"[LIVE] Player {player.id_in_group} - Training Penalty: {player.training_penalty}")
    
            # Show scoreboard if needed
            scoreboard = get_scoreboard(player)
    
            if data.get('end_exploration'):
                player.training_exploration = False
                player.training_performance_start = max(3000 - player.training_penalty, 0)  
                player.cum_payoff_training = player.training_performance_start
                print(f"[LIVE] Player {my_id} ended exploration via SPACEBAR. Moving to PERFORMANCE sub-phase.")
                return {my_id: dict(training_passed=True)}
                player.training_temp_log = json.dumps(player.participant.vars.get('training_temp_log', []))
                print('Saved training log:', player.participant.vars['training_temp_log'])
    
            if data.get('letter'):
                letter = data['letter']
                deck = player.deck_layout.index(letter)
                reward = C.TRAINING_REWARDS[deck]
                cost = C.TRAINING_COSTS[deck]
                payoff = reward - cost
    
                player.participant.vars['training_temp_log'].append(dict(
                    timestamp=round(time.time(), 2),
                    letter=letter,
                    deck=deck,
                    reward=float(reward),
                    cost=float(cost),
                    payoff=payoff
                ))
    
                print(f"[TRAINING] Player {my_id} (exploration) selected {letter}: Reward {reward}, Cost {cost}")
    
            return {my_id: dict(
                training=True,
                training_exploration=True,
                training_duration=round(training_duration, 2),
                reward=float(reward),
                cost=float(cost),
                payoff=payoff,
                penalty=player.training_penalty,
                cum_payoff=player.training_cum_payoff,
                scoreboard=scoreboard
            )}
    
    
        # === TRAINING PERFORMANCE SUB-PHASE ===
        scoreboard = []
        if data.get('end_training'):
            submitted_answer = data.get('best_deck_answer')
            correct_answer = player.deck_layout[player.deck_layout.index('A')]
    
            if submitted_answer == correct_answer:
                player.in_training = False
    
                player.end_time = time.time()
                player.training_passed = True
                total_time = player.end_time - player.training_start_time if player.training_start_time else 0
                player.in_exploration_phase = True
                print(f"[LIVE] Player {my_id} ended full training at {player.end_time}. Total training duration: {total_time:.2f} sec.")
                return {my_id: dict(training_complete=True, total_time=round(total_time, 2))}
            else:
                print(f"[LIVE] Player {my_id} answered incorrectly ({submitted_answer}). Restarting exploration.")
                player.training_exploration = True
                return {my_id: dict(
                    training_incorrect=True,
                    restart_exploration=True,
                    message="Incorrect. Please re-explore the decks and try again."
                )}
    
        if data.get('letter'):
            letter = data['letter']
            deck = player.deck_layout.index(letter)
            reward = C.TRAINING_REWARDS[deck]
            cost = C.TRAINING_COSTS[deck]
            payoff = reward - cost
    
            player.participant.vars['training_temp_log'].append(dict(
                timestamp=round(time.time(), 2),
                letter=letter,
                deck=deck,
                reward=float(reward),
                cost=float(cost),
                payoff=payoff
            ))
    
            player.cum_payoff_training += payoff
            print(f"[TRAINING] Player {my_id} (performance) selected {letter}: Reward {reward}, Cost {cost}, New cumulative: {player.cum_payoff_training}")
    
            scoreboard = get_scoreboard(player)
    
            return {my_id: dict(
                training=True,
                training_exploration=False,
                training_duration=round(training_duration, 2),
                cum_payoff=player.cum_payoff_training,
                scoreboard = scoreboard
            )}
    
        return {my_id: dict(
            training=True,
            training_exploration=False,    
            training_duration=round(training_duration, 2),
            cum_payoff=player.cum_payoff_training,
            scoreboard = scoreboard
        )}
    
    # === MAIN STUDY: EXPLORATION PHASE ===
    if player.in_exploration_phase:
        if player.field_maybe_none('start_time') is None:
            player.start_time = time.time()
            player.participant.vars['exploration_temp_log'] = []
            print(f"[LIVE] Player {my_id} start_time initialized to {player.start_time}.")
    
        player.exploration_duration = time.time() - player.start_time
        penalty = get_penalty(player)
        player.penalty = penalty
        cum_payoff = 3000 - penalty
    
    
        log_entry = dict(
            timestamp=round(time.time(), 2),
            exploration_duration=round(player.exploration_duration, 2),
            penalty=penalty,
            cum_payoff=cum_payoff
        )
        player.participant.vars['exploration_temp_log'].append(log_entry)
    
        # Rank for competition
        scoreboard = get_scoreboard(player)
    
        print(f"[LIVE] Player {my_id} - Exploration Duration: {player.exploration_duration:.2f}s, Penalty: {penalty}, Cum_Payoff: {cum_payoff}")
    
        if 'letter' not in data and not data.get('end_exploration'):
            return {my_id: dict(
                exploration=True,
                exploration_duration=round(player.exploration_duration, 2),
                penalty=penalty,
                cum_payoff=cum_payoff,
                scoreboard=scoreboard
            )}
    
    # === END OF EXPLORATION PHASE ===
    if data.get('end_exploration'):
        print(f"[LIVE] Player {my_id} pressed SPACE → ending exploration phase.")
        player.in_exploration_phase = False
        player.num_trials = 0
    
        if player.field_maybe_none('start_time'):
            player.exploration_duration = time.time() - player.start_time
            print(f"[LIVE] Player {my_id} spent {player.exploration_duration:.2f} seconds in exploration.")
        else:
            player.exploration_duration = 0
            print(f"[ERROR] Player {my_id} had no start_time logged.")
    
        player.exploration_log = json.dumps(player.participant.vars.get('exploration_temp_log', []))
        print('Saved exploration log:', player.participant.vars['exploration_temp_log'])
        penalty = get_penalty(player)  
        player.performance_starting_payoff = max(3000 - penalty, 0)  # Set only after exploration phase ends
        player.payoff = player.performance_starting_payoff
        player.participant.vars['performance_log'] = []
    
        print(f"[LIVE] Player {my_id} starting performance phase with payoff: {player.payoff}")
        return {my_id: dict(
            phase_switched=True,
            training_passed=True,
            exploration_duration=round(player.exploration_duration, 2),
            penalty=penalty
        )}
    
    # === PERFORMANCE PHASE: CARD SELECTION ===
    if not player.in_exploration_phase and not player.in_training:
        # Update scoreboard when a selection is made
        if 'letter' in data:
            letter = data['letter']
            print(f"[LIVE] Player {my_id} selected letter: {letter}")
    
            try:
                deck = player.deck_layout.index(letter)
                field_name = f'num{deck}'
                cur_count = getattr(player, field_name)
                reward = C.REWARDS[deck]
                cost = session.vars['iowa_costs'][deck][cur_count]
                payoff = reward - cost
    
                setattr(player, field_name, cur_count + 1)
                player.num_trials += 1
    
                if player.in_exploration_phase:
                    print(f"[EXPLORATION] Player {my_id} drew from deck {letter}. Not counted toward payoff.")
                else:
                    player.payoff += payoff
                    player.participant.vars['performance_log'].append(dict(
                        timestamp=round(time.time(), 2),
                        letter=letter,
                        deck=deck,
                        reward=float(reward),
                        cost=float(cost),
                        payoff=float(player.payoff),
                        num_trials=player.num_trials
                    ))
    
                penalty = get_penalty(player) 
                cum_payoff = max(3000 - penalty, 0) if player.in_exploration_phase else float(player.payoff)
                
                # Update scoreboard if in competition treatment
                scoreboard = get_scoreboard(player)
            
                resp = dict(
                    cost=float(cost),
                    reward=float(reward),
                    cum_payoff=cum_payoff,
                    num_trials=player.num_trials,
                    exploration=player.in_exploration_phase,
                    exploration_duration=round(player.exploration_duration, 2),
                    penalty=penalty if player.in_exploration_phase else 0,
                    scoreboard=scoreboard
                )
    
                print(f"[LIVE] Player {my_id} - Reward: {reward}, Cost: {cost}, Payoff: {payoff}")
                print(f"[LIVE] Trials: {player.num_trials}, Cumulative Payoff: {resp['cum_payoff']}")
    
                if player.num_trials == C.NUM_TRIALS:
                    player.performance_log = json.dumps(player.participant.vars.get('performance_log', []))
                    resp['finished'] = True
                    print(f"[LIVE] Player {my_id} finished all trials.")
    
                return {my_id: resp}
    
            except Exception as e:
                print(f"[ERROR] Processing player {my_id}: {e}")
                return {my_id: dict(error=str(e))}
            
       # === Passive scoreboard update if no card selected ===
        if player.field_maybe_none('performance_start_time') is None:
            player.performance_start_time = time.time()  # Initialize if not already set
            print(f"[LIVE] Player {my_id} performance phase started.")
        
        cum_payoff = float(player.payoff)
        scoreboard = get_scoreboard(player)
        
        response = {
            my_id:dict(
                performance = True,
                cum_payoff = cum_payoff,
                scoreboard = scoreboard  # update scoreboard in real-time
            )
        }

        return response
    
    # === DEFAULT RETURN ===
    return {my_id: {}}

def get_scoreboard(player: Player):
    group = player.group
    # Update scoreboard for group under competition
    scoreboard = None
    if player.competition:
        all_scores = []
        for p in player.group.get_players():
            #==  Training phase   ==
            if player.in_training: 
                if p.training_exploration:
                    temp_trainning_penalty = get_penalty(player)
                    temp_training_cum_payoff = 3000 - temp_trainning_penalty
                    all_scores.append((p.id_in_group, temp_training_cum_payoff))
                else:
                    # For training performance, use training cumulative payoff
                    all_scores.append((p.id_in_group, float(p.cum_payoff_training)))
            #==  Main study == 
            elif p.in_exploration_phase:
                if p.field_maybe_none('start_time') is not None:
                   # changed: duration = time.time() - p.start_time
                   temp_penalty = get_penalty(player) #changes
                   temp_cum_payoff = max(3000 - temp_penalty, 0)
                   all_scores.append((p.id_in_group, temp_cum_payoff))
                else:
                   all_scores.append((p.id_in_group, 3000))
            else:
                all_scores.append((p.id_in_group, float(p.payoff)))
        ranked = sorted(all_scores, key=lambda x: x[1], reverse=True)
        scoreboard = [{'id': pid, 'payoff': s, 'rank': i+1} for i, (pid, s) in enumerate(ranked)]
    return scoreboard
def start_training(player: Player):
    session = player.session
    group = player.group
    participant = player.participant
    # Initialize training session
    import time
    player.training_exploration = True
    player.training_start_time = time.time()
    player.participant.vars['training_temp_log']=[]
    print(f"[LIVE] Player {player.id_in_group} started training at {player.training_start_time}.")
class IntroductionPage(Page):
    form_model = 'player'
    @staticmethod
    def vars_for_template(player: Player):
        participant = player.participant
        return {
                'timeout_message': player.participant.vars.get('timeout_message')
            }
class TrainingExploration(Page):
    form_model = 'player'
    live_method = 'live_method'
class TrainingPerform(Page):
    form_model = 'player'
    live_method = 'live_method'
class ExplorationPhase(Page):
    form_model = 'player'
    live_method = 'live_method'
class TrasitionPage(Page):
    form_model = 'player'
    @staticmethod
    def is_displayed(player: Player):
        return not player.in_exploration_phase
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        group = player.group
        participant = player.participant
        if player.participant.vars.get('phase_switched'):
            print(f"[DEBUG] Switching to performance phase for Player {player.id_in_group}")
            player.in_exploration_phase = False
            player.num_trials = 0  # Reset trial count for performance phase if desired
class PerformancePhase(Page):
    form_model = 'player'
    live_method = 'live_method'
    @staticmethod
    def is_displayed(player: Player):
        return not player.in_exploration_phase
class ResultPage(Page):
    form_model = 'player'
page_sequence = [IntroductionPage, TrainingExploration, TrainingPerform, ExplorationPhase, TrasitionPage, PerformancePhase, ResultPage]
