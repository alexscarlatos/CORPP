import sys
import corpp

def getStateNames(states):
    return ["_".join(s[0]) for s in states]

def getStateProbs(states):
    return ["{:10.4f}".format(s[1]).strip() for s in states]

def getStateRoundedSum(states):
    return sum([float(p) for p in getStateProbs(states)])

if __name__ == "__main__":
    # variables specific to shopping requests test case
    init_state_vars = [
        ("What is the time of day (morning, noon, or night)?\n    ", "currentTime", ["morning", "noon", "night"]),
        ("Who am I speaking with?\n    ", "currentPerson", [])
    ]
    worldVariables = ["item", "room", "person"]
    nameOfPrologFile = "shopping_requests"
    nameOfGetPredicate = "getTasks"
    nameOfPOMDPFile = "shopping_requests"
    defaultsFilename = "defaults.txt"

    # variables that can be set from command line params
    verbose = False
    verbosePOMDP = False
    pathToXSB = "xsb"
    pathToPOMDPSolve = "pomdp-solve"
    domainFilename = "domain_1.txt"
    initialFactsFilename = "initial_facts_1.txt"
    epsilon = 50
    rewards = ["-10","-1","50","-100"]

    # get parameters from command line
    for i, a in enumerate(sys.argv):
        if a == "-v":
            verbose = True
        if a == "-vp":
            verbosePOMDP = True
        if a == "-xsb" and i < len(sys.argv) - 1:
            pathToXSB = sys.argv[i + 1]
        if a == "-pomdp" and i < len(sys.argv) - 1:
            pathToPOMDPSolve = sys.argv[i + 1]
        if a == "-dom" and i < len(sys.argv) - 1:
            domainFilename = sys.argv[i + 1]
        if a == "-facts" and i < len(sys.argv) - 1:
            initialFactsFilename = sys.argv[i + 1]
        if a == "-epsilon" and i < len(sys.argv) - 1:
            epsilon = int(sys.argv[i + 1])
        if a == "-r" and i < len(sys.argv) - 1:
            rewards = sys.argv[i + 1].split(',')

    # get possible worlds from LR/PR
    domain, possibleWorlds = corpp.getPossibleWorlds(nameOfPrologFile, nameOfGetPredicate, init_state_vars=init_state_vars, domainFilename=domainFilename, initialFactsFilename=initialFactsFilename, defaultsFilename=defaultsFilename, pathToXSB=pathToXSB, verbose=verbose)

    # states are all possible worlds plus the terminating state
    states = possibleWorlds
    # normalize state probabilities
    state_sum = sum([s[1] for s in states])
    states = [(s[0], s[1]/state_sum) for s in states]
    # pomdp-solve will yell at us if our state probabilities don't add to 1
    # so if we went under then add to term, and if we went over take away from first state (amts should be negligible)
    rounded_state_sum = getStateRoundedSum(states)
    if rounded_state_sum > 1:
        states[0] = (states[0][0], states[0][1] + (1 - rounded_state_sum))
        states.insert(0, (["term"], 0))
    else:
        states.insert(0, (["term"], 1 - rounded_state_sum))

    # actions are all which questions, polar questions, and possible deliveries
    which_qs = []
    for k in worldVariables:
        which_qs.append("which_" + k)
    polar_qs = []
    for k in worldVariables:
        for v in domain[k]:
            polar_qs.append("is_" + k + "_" + v)
    delivery_actions = []
    for s in getStateNames(states):
        if s != "term":
            da = "deliver_" + s
            delivery_actions.append(da)
    actions = which_qs + polar_qs + delivery_actions

    # observations are possible answers to all questions
    observations = []
    observations.append("none")
    observations.append("yes")
    observations.append("no")
    for k in worldVariables:
        for v in domain[k]:
            observations.append(v)

    # build pomdp input file
    with open(nameOfPOMDPFile + ".POMDP", "w") as pomdp_file:
        if verbose:
            print("Initializing POMDP...")
        pomdp_file.write("discount: 0.95\n\n")
        pomdp_file.write("values: reward\n\n")
        pomdp_file.write("states: " + " ".join(getStateNames(states)) + "\n\n")
        pomdp_file.write("actions: " + " ".join(actions) + "\n\n")
        pomdp_file.write("observations: " + " ".join(observations) + "\n\n")

        pomdp_file.write("start: " + " ".join(getStateProbs(states)) + "\n\n")

        # T: <action> : <start-state> : <end-state> %f
        # asking questions does not change state
        for q in which_qs:
            pomdp_file.write("T: " + q + " identity\n")
        for q in polar_qs:
            pomdp_file.write("T: " + q + " identity\n")
        # all deliveries from any start state result in term
        for da in delivery_actions:
            pomdp_file.write("T: " + da + " : * : term 1.0\n")

        # O: <action> : <end-state> : <observation> %f
        d = 0 # 0: item, 1: room, 2: person
        for q in which_qs:
            pomdp_file.write("O: " + q + "\n")
            pomdp_file.write("1.0" + " 0.0" * (len(observations) - 1) + "\n") # 'none' observation for term state
            for s in states[1:]:
                # you answered with observation o if you end up in a state that corresponds to o
                pomdp_file.write(" ".join(["1.0" if s[0][d] == o else "0.0" for o in observations]) + "\n")
            d += 1

        for q in polar_qs:
            pomdp_file.write("O: " + q + "\n")
            pomdp_file.write("1.0 " + "0.0 " * (len(observations) - 1) + "\n") # 'none' observation for term state
            q_ = q.split("_")
            d = worldVariables.index(q_[1])
            for s in states[1:]:
                # if you end in a state that corresponds to the question, you answered yes, otherwise no
                answer = "0.0 1.0 0.0" if s[0][d] == q_[2] else "0.0 0.0 1.0"
                pomdp_file.write(answer + " 0.0" * (len(observations) - 3) + "\n")

        for da in delivery_actions:
            pomdp_file.write("O: " + da + " uniform\n")

        # R: <action> : <start-state> : <end-state> : <observation> %f
        # slight disincentive to ask questions
        for q in which_qs:
            pomdp_file.write("\nR: " + q + " : * : * : * " + rewards[0])
        for q in polar_qs:
            pomdp_file.write("\nR: " + q + " : * : * : * " + rewards[1])
        # for each delivery action, give incentive to transition to corresponding state, and disincentive to transition to any other state
        for da in delivery_actions:
            ds = da.split("_", 1)[1]
            for s in getStateNames(states[1:]):
                pomdp_file.write("\nR: " + da + " : " + s + " : term : * " + (rewards[2] if ds == s else rewards[3]))

    # get policy graph from PP
    policy, cur_node, cur_action = corpp.getPolicyGraph(nameOfPOMDPFile, [s[1] for s in states], pathToPOMDPSolve=pathToPOMDPSolve, epsilon=epsilon, verbose=verbose, verbosePOMDP=verbosePOMDP)

    if policy == []:
        exit()

    # given an action, execute and return the observation made
    def executeAction(a):
        vals = a.split("_")
        ans = ""

        # which questions
        if len(vals) == 2:
            expected_domain = domain[vals[1]]
            if vals[1] == "item":
                qs = "Which item should be delivered?"
            else:
                qs = "Which " + vals[1] + " should this item be delivered to?"
            ans = input(qs + "\n")
            if not ans in expected_domain:
                print("Invalid answer") # TODO: instead, try to update domain
                return executeAction(a)
        # polar questions
        elif len(vals) == 3:
            expected_domain = ["yes", "no"]
            if vals[1] == "item":
                qs = "Is the item a " + vals[2] + "?"
            else:
                qs = "Is this delivery for " + vals[2] + "?"
            ans = input(qs + "\n")
            if not ans in expected_domain:
                print("Answer must be yes or no")
                return executeAction(a)
        
        # get associated observation from user answer
        try:
            obs = observations.index(ans)
        except:
            obs = -1
        return obs

    print("\nHello user!")

    # follow rules until we reach termination
    terminating_actions = [i for i in range(len(which_qs) + len(polar_qs), len(actions))]
    while cur_action not in terminating_actions:
        # execute the current action and get the observation
        obs = executeAction(actions[cur_action])
        if obs == -1:
            print("err") # TODO: handle better
        else:
            # based on observation, go to next node and continue
            cur_node = policy[cur_node][1][obs]
            if cur_node == -1:
                print("policy graph nav err") # TODO: handle better
            cur_action = policy[cur_node][0]
    
    print("Made delivery! (" + actions[cur_action] + ")")
