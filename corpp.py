import subprocess
import re
import os
import time

# ------ POMDP INIT CLASS ------

# for making a pomdp init file easier
class PomdpInit:
    def __init__(self):
        self.discount = "0.95"
        self.values = "reward"
        self.states = []
        self.actions = []
        self.observations = []
        self.initStateProbs = []
        self.transitions = []
        self.transitionRows = []
        self.transitionMats = []
        self.observationTrans = []
        self.observationsTransRows = []
        self.observationTransMats = []
        self.rewards = []

    def setDiscount(self, d):
        self.discount = d
    
    def setValues(self, v):
        self.values = v

    def setStates(self, s):
        if not isinstance(s, list):
            print("Value Error: States must be a list of state names")
        else:
            self.states = s

    def setActions(self, a):
        if not isinstance(a, list):
            print("Value Error: Actions must be a list of action names")
        else:
            self.actions = a

    def setObservations(self, o):
        if not isinstance(o, list):
            print("Value Error: Observations must be a list of observation names")
        else:
            self.observations = o

    def addTransitionIdentity(self, a):
        self.transitions.append(a + " identity")

    def addTransitionUniform(self, a):
        self.transitions.append(a + " uniform")
    
    def addTransition(self, a, start, end, prob):
        self.transitions.append(a + " : " + start + " : " + end + " " + prob)

    def addTransitionRow(self, a, start, row):
        self.transitionRows.append((a + " " + start, row))

    def addTransitionMatrix(self, a, mat):
        self.transitionMats.append((a, mat))

    def addObservationTransition(self, a, end, o, prob):
        self.observationTrans.append(a + " : " + end + " : " + obs + " " + prob)
    
    def addObservationTransitionRow(self, a, end, row):
        self.observationsTransRows.append((a + " " + end, row))

    def addObservationTransitionMat(self, a, mat):
        self.observationTransMats.append((a, mat))

    def addReward(self, a, start, end, o, val):
        self.rewards.append(a + " : " + start + " : " + end + " : " + o + " " + val)

    def generateFile(self, nameOfPOMDPFile):
        filename = nameOfPOMDPFile + ".POMDP"
        with open(filename) as pomdp_file:
            pomdp_file.write("discount: " + self.discount + "\n\n")
            pomdp_file.write("values: " + self.values + "\n\n")
            pomdp_file.write("states: " + " ".join(self.states) + "\n\n")
            pomdp_file.write("actions: " + " ".join(self.actions) + "\n\n")
            pomdp_file.write("observations: " + " ".join(self.observations) + "\n\n")
            for t in self.transitions:
                pomdp_file.write("T: " + t + "\n")
            for t in self.transitionRows:
                pomdp_file.write("T: " + t[0] + "\n")
                pomdp_file.write(" ".join(t[1]) + "\n")
            for t in self.transitionMats:
                pomdp_file.write("T: " + t[0] + "\n")
                for r in t[1]:
                    pomdp_file.write(" ".join(r) + "\n")
            for o in self.observationTrans:
                pomdp_file.write("O: " + o + "\n")
            for o in self.observationsTransRows:
                pomdp_file.write("O: " + o[0] + "\n")
                pomdp_file.write(" ".join(o[1]) + "\n")
            for o in self.observationTransMats:
                pomdp_file.write("O: " + o[1])
                for r in o[1]:
                    pomdp_file.write(" ".join(r) + "\n")
            for r in self.rewards:
                pomdp_file.write("R: " + r + "\n")
        return filename


# ------ HELPER FUNCTIONS ------

# assuming each world has format "(a1,a2,...,prob)"
# return tuple of format ([a1,a2,...], prob)
def getWorldTuple(world):
    vals = world.strip("()").rsplit(",", maxsplit=1)
    return (vals[0].split(","), float(vals[1]))

def fact(name, params):
    return name + "(" + ','.join(params) + ")"

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


# ------ MAIN FUNCTIONS ------

# TODO: add options 'includeTerm', 'dynamicDomain', 'normalizeProbs'
def getPossibleWorlds(nameOfPrologFile, nameOfGetPredicate, init_state_vars=[], defaultsFilename="defaults.txt", domainFilename="domain.txt", initialFactsFilename="initial_facts.txt", pathToXSB="xsb", verbose=False):
    # first step is to obtain defaults for LR/PR
    defaults = []

    # read database of variables and possible values
    domain = {}
    with open(domainFilename, "r") as domain_file:
        if verbose:
            print("Retrieved initial domain:")
        for line in domain_file:
            # each line has variable name, followed by list of predefined values
            l = line.strip('\n').split(':')
            domain[l[0]] = []
            for v in l[1].split(','):
                defaults.append(fact(l[0], [v]))
                domain[l[0]].append(v)
            if verbose:
                print("    " + l[0] + ": " + l[1])
        
    # read database of facts - each line is prolog fact
    with open(initialFactsFilename, "r") as initial_facts_file:
        if verbose:
            print("Retrieved initial facts:")
        for line in initial_facts_file:
            f = line.strip('\n')
            defaults.append(f)
            if verbose:
                print("    " + f)
    
    # ask for necessary state variables
    for sv in init_state_vars:
        v = input(sv[0])
        v = v.replace(" ", "_") # TODO: will have to do more than this to guarantee valid value (apply all valid Prolog atom rules)
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
    possibleWorlds = [getWorldTuple(world) for world in possibleWorlds if len(world) > 0]

    if verbose:
        print("Generated possible worlds:")
        print('\n'.join(["    " + str(s[0]) + ": " + str(s[1]) for s in possibleWorlds]))

    return domain, possibleWorlds


def getPolicyGraph(nameOfPOMDPFile, initialBeliefState, pathToPOMDPSolve="pomdp-solve", epsilon=50, verbose=False, verbosePOMDP=False):
    # start pomdp-solve
    if verbose:
        print("Running pomdp-solve... (May take a while)\n")
    else:
        print("Thinking, please wait...")
    currentTime = time.time()
    pomdpParams = [pathToPOMDPSolve, '-pomdp', nameOfPOMDPFile + ".POMDP", '-epsilon', str(epsilon)]
    if verbosePOMDP:
        proc = subprocess.Popen(pomdpParams)
    else:
        proc = subprocess.Popen(pomdpParams, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    deal = proc.communicate()[0]
    if verbose:
        print("pomdp-solve complete, execution time: {:10.4f}s \n".format(time.time() - currentTime))
    
    # find pomdp output files
    pg_filename = ""
    alpha_filename = ""
    # TODO: what should dir be?
    for f in os.listdir("."):
        if f.startswith(nameOfPOMDPFile) and f.endswith(".pg"):
            pg_filename = f
        elif f.startswith(nameOfPOMDPFile) and f.endswith(".alpha"):
            alpha_filename = f
    if len(pg_filename) == 0 or len(alpha_filename) == 0:
        print("Error: couldn't find pomdp output files!")
        return [], -1, -1

    # build state machine from policy graph
    policy = []
    with open(pg_filename) as pg_file:
        for line in pg_file:
            vals = re.split("[ \t]+", line.strip())
            policy.append((int(vals[1]), [getNodeNum(n) for n in vals[2:]]))
    if verbose:
        print("Generated policy graph:")
        for i, n in enumerate(policy):
            print("    " + str(i) + " - " + str(n[0]) + " - " + str(n[1]))

    # get starting node/action
    cur_node = getStartingPolicyNode(alpha_filename, initialBeliefState)
    cur_action = policy[cur_node][0]
    if verbose:
        print("Starting at node " + str(cur_node))

    # delete pg and alpha files (so we can run POMDP again without confusing outputs)
    delOutputFiles = True
    if delOutputFiles:
        os.remove(pg_filename)
        os.remove(alpha_filename)

    return policy, cur_node, cur_action