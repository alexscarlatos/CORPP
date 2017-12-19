import sys
import os
import subprocess
import re
import numpy as np
import corpp

pathToXSB = "../../../xsb/bin/xsb"
nameOfPrologFile = "shopping_requests"
nameOfGetPredicate = "getTasks"

pathToPOMDPSolve = "../../../pomdp-solve-5.4/src/pomdp-solve"
nameOfPOMDPFile = "shopping_requests"

domainFilename = "domain_test.txt"
initialFactsFilename = "initial_facts_test.txt"
defaultsFilename = "defaults.txt"

init_state_vars = [
    ("What is the time of day (morning, noon, or night)?\n", "currentTime", ["morning", "noon", "night"]),
    ("Who am I speaking with?\n", "currentPerson", [])
]

worldVariables = ["item", "room", "person"]

def fact(name, params):
    return name + "(" + ','.join(params) + ")"

# assuming each world has format "(a1,a2,...,prob)"
# return tuple of format ([a1,a2,...], prob)
def getWorldTuple(world):
    vals = world.strip("()").rsplit(",", maxsplit=1)
    return (vals[0].split(","), float(vals[1]))

def getStateNames(states):
    return ["_".join(s[0]) for s in states]

def getStateProbs(states):
    return ["{:10.4f}".format(s[1]).strip() for s in states]

def getStateRoundedSum(states):
    return sum([float(p) for p in getStateProbs(states)])

def getStartingPolicyNode(alpha_filename, initialBelief):
    with open(alpha_filename) as alphaFile:
        bestNode = 0
        maxDotProd = 0
        nodeIndex = 0
        lineState = 1

        # file format is <actionIndex>\n<stateVector>\n[repeat...]
        # the best starting node is the one whose vector has the highest dot product with the initial belief state
        for line in alphaFile:
            if lineState == 2:
                vals = line.split(' ')
                dotProd = sum([float(a) * b for (a,b) in zip(vals, initialBelief)])
                if dotProd > maxDotProd:
                    maxDotProd = dotProd
                    bestNode = nodeIndex
            
            lineState += 1
            if lineState == 3:
                lineState = 0
                nodeIndex += 1
        
        return bestNode

# because nodes can have a value of >= 0 or '-'
def getNodeNum(node):
    try:
        return int(node)
    except:
        return -1

if __name__ == "__main__":
    verbose = len(sys.argv) > 1 and sys.argv[1] == "-v"

    # first step is to obtain defaults for LR/PR
    defaults = []

    # read database of variables and possible values
    domain = {}
    with open(domainFilename, "r") as domain_file:
        for line in domain_file:
            # each line has variable name, followed by list of predefined values
            l = line.strip('\n').split(':')
            domain[l[0]] = []
            for v in l[1].split(','):
                defaults.append(fact(l[0], [v]))
                domain[l[0]].append(v)
    if verbose:
        print("Retrieved initial domain:")
        print(domain)
    
    # read database of facts - each line is prolog fact
    with open(initialFactsFilename, "r") as initial_facts_file:
        for line in initial_facts_file:
            defaults.append(line.strip('\n'))
    # TODO: if verbose: print("Retrieved initial facts:") ...
    
    # ask for necessary state variables
    for sv in init_state_vars:
        v = input(sv[0])
        v = v.replace(" ", "_")
        if len(sv[2]) > 0:
            while (not v in sv[2]):
                print("Improper value, please try again")
                v = input(sv[0])
        defaults.append(fact(sv[1], [v]))

    # write defaults to file
    with open(defaultsFilename, "w") as defaults_file:
        defaults_file.write(".\n".join(defaults) + ".")

    # launch Prolog
    proc = subprocess.Popen([pathToXSB], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    # run LR/PR program
    prologFileCmd = "[" + nameOfPrologFile + "]."
    predicateCmd = nameOfGetPredicate + "('" + defaultsFilename + "',W)."
    fullCmd = "{}\n{}".format(prologFileCmd, predicateCmd)
    if verbose:
        print("Running LR/PR in XSB...\n")
    prologOutput = proc.communicate(input=str.encode(fullCmd))[0].decode()

    # retrieve possible worlds from Prolog output
    inputStart = prologOutput.index('[')
    inputEnd = prologOutput.index(']')
    possibleWorlds = re.split(',*task', prologOutput[inputStart+1:inputEnd])

    # states are all possible worlds, along with associated initial probability, plus the terminating state
    states = [getWorldTuple(world) for world in possibleWorlds if len(world) > 0]
    # normalize state probabilities
    state_sum = sum([s[1] for s in states])
    states = [(s[0], s[1]/state_sum) for s in states]
    rounded_state_sum = getStateRoundedSum(states)
    if rounded_state_sum > 1:
        # TODO: handle
        print("rounded state sum > 1")
    states.insert(0, (["term"], 1 - rounded_state_sum)) # term prob should be 0, but we add in extra amt here to make proper sum
    
    if verbose:
        print("Generated possible worlds:")
        print('\n'.join([str(s[0]) + ": " + str(s[1]) for s in states]))

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
            pomdp_file.write("\nR: " + q + " : * : * : * -1")
        for q in polar_qs:
            pomdp_file.write("\nR: " + q + " : * : * : * -2")
        # for each delivery action, give incentive to transition to corresponding state, and disincentive to transition to any other state
        for da in delivery_actions:
            ds = da.split("_", 1)[1]
            for s in getStateNames(states[1:]):
                pomdp_file.write("\nR: " + da + " : " + s + " : term : * " + ("50" if ds == s else "-100"))

    # start pomdp-solve
    # TODO: set upper bound on horizon?
    if verbose:
        print("Running pomdp-solve... (May take a while)\n")
    else:
        print("Thinking, please wait...")
    showPomdpOutput = True
    if showPomdpOutput:
        proc = subprocess.Popen([pathToPOMDPSolve, '-pomdp', nameOfPOMDPFile + ".POMDP"])
    else:
        proc = subprocess.Popen([pathToPOMDPSolve, '-pomdp', nameOfPOMDPFile + ".POMDP"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    deal = proc.communicate()[0]
    if verbose:
        print("pomdp-solve complete\n")
    
    # find pomdp output files
    pg_filename = ""
    alpha_filename = ""
    for f in os.listdir("."):
        if f.startswith(nameOfPOMDPFile) and f.endswith(".pg"):
            pg_filename = f
        elif f.startswith(nameOfPOMDPFile) and f.endswith(".alpha"):
            alpha_filename = f
    if len(pg_filename) == 0 or len(alpha_filename) == 0:
        print("Error: couldn't find pomdp output files! Quitting...")
        exit()

    # build state machine from policy graph
    policy = []
    with open(pg_filename) as pg_file:
        for line in pg_file:
            vals = re.split("[ \t]+", line.strip())
            policy.append((int(vals[1]), [getNodeNum(n) for n in vals[2:]]))
    if verbose:
        print("Generated policy graph:")
        for i, n in enumerate(policy):
            print(str(i) + " - " + actions[n[0]] + " - " + str(n[1]))

    # get starting node/action
    cur_node = getStartingPolicyNode(alpha_filename, [s[1] for s in states])
    cur_action = policy[cur_node][0]
    if verbose:
        print("Starting at node " + str(cur_node))

    # delete pg and alpha files (so we can run POMDP again without confusing outputs)
    delOutputFiles = True
    if delOutputFiles:
        os.remove(pg_filename)
        os.remove(alpha_filename)

    print("Hello user!")

    terminating_actions = [i for i in range(len(which_qs) + len(polar_qs), len(actions))]

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

    # follow rules until we reach termination
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
