:- table validTask/3.
:- dynamic item/1, person/1, room/1, timeOfDay/1, place/2, registered/1, paid/1, prof/1, student/1, currentTime/1, currentPerson/1.

% get all possible tasks and their associated probabilities
getTasks(F, W) :-
    seeing(OF),
    see(F),
    initialize,
    read_and_load,
    findall(task(I,R,P,Pr), task(I,R,P,Pr), W),
    seen,
    see(OF).

% rectract all previously asserted facts
initialize :-
    retractall(item(_)),
    retractall(person(_)),
    retractall(room(_)),
    retractall(timeOfDay(_)),
    retractall(place(_,_)),
    retractall(registered(_)),
    retractall(paid(_)),
    retractall(prof(_)),
    retractall(student(_)),
    retractall(currentTime(_)),
    retractall(currentPerson(_)).

% assert fact for each line in file
read_and_load :-
    read(T),
    (
        T = end_of_file
        ->
        true
        ;
        assert(T),
        read_and_load
    ).

% assumption is that each possible task can be assigned at least one probability
% return product of all probabilities for given tuple
task(Item, Room, Person, FinalProb) :-
    validTask(Item, Room, Person),
    findall(Pr, task_p(Item, Room, Person, Pr), SubTasks),
    \+ SubTasks = [],
    product(SubTasks, FinalProb).

% get the cumulative product of a list of numbers
product(L, R) :-
    product(L, 1, R).
product([], Final, Final).
product([H|T], Cur, Final) :-
    Cur1 is Cur * H,
    product(T, Cur1, Final).

% asserts that the given tuple is a possible task
validTask(Item, Room, Person) :-
    item(Item),
    room(Room),
    authorized(Person).

% logical reasoning - determine if the given person is allowed to make a request
authorized(Person) :-
    paid(Person),
    prof(Person).
authorized(Person) :-
    registered(Person),
    student(Person).

% predefined probabilities for all items at all times
probAtTime(coffee, morning, .8).
probAtTime(sandwich, morning, .2).
probAtTime(coffee, noon, .4).
probAtTime(sandwich, noon, .6).
probAtTime(coffee, night, .2).
probAtTime(sandwich, night, .8).

probAtTime(Item, Prob) :- currentTime(T), probAtTime(Item, T, Prob).
defaultItemProb(.5).

% probability associations for place
task_p(Item, Room, Person, Prob) :-
    place(Person, Room)
    ->
    Prob = .8
    ;
    Prob = .2.

% probability associations for item
task_p(Item, Room, Person, Prob) :-
    probAtTime(Item, Prob) % references currentTime
    ->
    true
    ;
    defaultItemProb(Prob).

% probability associations for person
task_p(Item, Room, Person, Prob) :-
    currentPerson(Person)
    ->
    Prob = .7
    ;
    Prob = .3.