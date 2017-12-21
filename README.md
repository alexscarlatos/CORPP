# CORPP
## Description
This project is an implementation of the algorithm described in the paper "CORPP: Commonsense Reasoning and Probabilistic Planning, as Applied to Dialog with a Mobile Robot". There are a few slight changes in the way implementation was approached (I used a single Prolog program for LR/PR rather than ASP and P-Log) but the overall outcome is the same.

I implemented the Shopping Requests test case described in the paper.

## Usage
To run the Shopping Requests example, you will need XSB Prolog (http://xsb.sourceforge.net) and pomdp-solve (http://www.pomdp.org/code/index.html). I did not include these as they are platform dependent, and pomdp-solve even recommends that you compile their C code on your machine to get an executable.

Simply run the program like so: '''python shopping_requests.py <options>'''  
Note: The program will only run with python3

There are several command line options you can use:  
-xsb: path to xsb executable  
-pomdp: path to pomdp-solve executable  
-epsilon: a value that determines acceptable error for POMDP solving, the higher this is the more error will be allowed, min val is 0  
-r: specify the rewards in a comma-separated list (ex: -10,-20,70,-60). the first value is the "reward" for asking 'which' questions, the second is the "reward" for asking 'is' questions, the third is the "reward" for making correct deliveries, and the fourth is the "reward" for making incorrect deliveries. changing these values is how you modify the overall behavior of the bot  
-dom: path to the domain file. there are several examples included  
-facts: path to the facts file. there are several examples included  
-v: print out information regarding calculations and internal data as you interact with the bot  
-vp: print out information specifically regarding to POMDP execution (you may want to see its progress)  


## Development
You may use the provided code to implement your own uses for CORPP! I tried to modularize the CORPP-specific code as much as possible, and it is contained in the corpp.py file, which can be referenced by other Python code. However, to use it you will still need some knowledge of how the algorithm works. I recommend reading the paper that I referenced before attempting to use this algorithm to develop. Or you can read the paper I wrote on my implementation, which is included in this repository.

You will also need to have good knowledge of how to initialize the podmp solver. Specifications on how to do so are here: http://www.pomdp.org/code/pomdp-file-spec.html. I also recommend using the shopping_requests.py code as reference.
