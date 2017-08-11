WHALER
======
(working title)

                          |                               
                    |     |                               
                    | .---'''--.                          
                .-----|        |                          
                |     ;,,..--..|                          
                ;...-.----''\'--.                         
               .-----|      |\  |                         
               |     ;,,..--| \.|                         
               ;...-.----'';|  \'.                        
              .-----|      ||   \|                        
              |     ;,,..-.||    \                        
              ;...-.----'''||_    \.                      
             .-----|       |_ `-._ \                      
             ;     ;,,..--.|_`-._ \-\                     
            ;__,,..----''''| `-._\-\ \                    
            .-----|        |    \ \ \ _,                  
            |     ;___...-.'-..__\_\,'                    
           ._--'''|   ___,|,---''';                       
            :````--'''  _____,--'/                        
    ~~~~~~~~~~:`-------'''        ;~~~~~~~~~~~~~~~~~~~    
    ~~~~~  ~~~ :__________________; ~~~~   ~~~~~ ~~~~    
    ~~   ~~~~~    ~~~~~    ~~~~~     ~~~~~~~ ~ ~~~~ ~~    
    ~ ~~~~~~ ~~~~~~   ~~  ~~~    ~~~~     ~~~   ~~~~ ~    

The game aims to simulate the life on a whaler sailing
ship. It aims to give a faithful image of the skills, 
hardships and determination of those who mastered the 
whaling trade, while picturing the brutality of this near
barbaric practice and tell the tail of the industrial
revolution from the viewport of a man on a ship's deck at
sea.

The plot is driven by a very simple story of a seaman 
(player), who starts out as a boy entering into service 
and follows his adventures at see as he climbs the ranks
of a ship and masters seamanship. The camera perspective
is player centered instead of the ship, first-pension or
chase cam or both with the ability to switch between them.
Including a birds eye perspective (with literal seagull or
albatross) solely for aesthetics as an extra feature. 

To achieve the goal the following mechanics and systems
are used:

   * physics system
       - fluid simulation system
       - wind simulation system
       - character tumble system
   * world simulation system
       - navigation mechanics
       - weather system
       - migration system
   * character interaction system
       - dialog system
       - respect (experience) mechanics
       - ai system


Physics System
--------------

This is a core feature. To reach the goal an immersive 
approximation of an intricate physics has to be simulated.
Heavy computational requirement might result a trade off
in terms of aesthetics (e.g. lighting). 

### Fluid Simulation System

Has three aspects: motion of fluid (sea) in various
weather conditions, interaction with the ship
(buoyancy and collision), interaction with characters.
The waves washing the decks should be able to knock
characters off.

### Wind Simulation System

One of the main aspects of the gameplay is maneuvering the
ship, therefore a pre-sail simulation is needed.
 
### Character Tumble System

The different characters should be able to tumble under
the various forces, including their own motion. Rag-doll
effects might be pre-baked, but a stability has to be
calculated dynamically per-character. 


World Simulation System
-----------------------

These are extra features, might be replaced with much
simplified versions.

The map is procedurally generated to encourage re-play and
enable sandbox like game-mode. It's cube-sphere shaped.

### Navigation Mechanics

Parts of the map is revealed when the location of the ship
is determined using navigation tools like sextant, pocket
watch and the sky. The sky is not procedurally generated,
but needs to be calculated properly in relation of
location time of the year and day.

### Weather System

Local weather is subject to location and time of the year.
Global weather is simulated to some extent e.g. ability
to sail around a storm.

### Migration System

On the map there are resource nodes (point) that may
change their richness between each other in relation to 
time of the year and whaling intensity.


Character Interaction System
----------------------------

The player and NPCs are all collectively considered
characters, therefore the interaction between them can
mean various things. Nevertheless it's fairly homogeneous
system. The control of the ship is tightly linked to 
character interactions, since it's done by issuing orders
to subordinates. That is done through the main HUD of the
GUI, and similarly it can be used to give advise for
superiors in rank when asked or on own initiative.
These actions among others are valuated by the respect
mechanics. The level of respect a character has effects
the rank in the crew they can fill, mainly because other
characters having higher respect then their superior can
challenge them to take their rank. Player has access to
perform any task or issue any order below his current
rank.

### Dialog System

Any interaction may result a response, in these cases
multiple variants are available and the game chooses
randomly and suppresses the chosen respond's probability
in subsequent choices (e.g. by randomly skipping in a
list). In some interaction a dialog graph might be used.

### Respect (experience) Mechanics

Assessing a situation either by carrying out a given order
or acting on ones own initiative is valuated by the game
and results a change in the respect value of the
character, success and acting near optimally raises the
character's respect, failing a task or performing badly
results loosing respect.

Charismatic interaction is a special kind of interaction.
It consist of some kind of fast paste mini game like 
brick breaker or tetris and gets incrementally harder.
Each increment increases the effect of the interaction. It
can be either rallying or scolding and it boosts or
dampens the respect change of an action e.g. when a
subordinate fails carrying out an order that would cause
a lose for the player also, but scolding him would reflect
that change to the subordinate.

The respect of NPCs effects the their performance. To be 
in align with the player's respect changes NPCs have two
non-changing attributes: skill and charisma. The skill
attribute is a multiplier that's applied to the NPC's
respect, therefore modifying his effectiveness and the
same time controls the likely progress of the character.
The charisma attribute does the same for charismatic
interactions of the NPC.

### AI System

The AI system enables the NPC's to perform their tasks.
It can carry out orders and issue the correct orders for
a given situation. Meanwhile it is scalable by the NPC
attributes and respect value. However it does not attempt
to find the optimal actions, those are hard-coded. It can
be viewed as an expert system for playing the game.


GUI
---

The game consist of performing a lot of small task that
require some kind of GUI, but these are mostly small icons
highlighting interaction points with the ship. The main
control mechanics of the game is issuing orders, that's
done through the main HUD. 

### Main HUD

The main HUD is a journal or notebook, that doubles as a
seamanship manual and gets new pages added as the player
progresses in rank. Orders can be issued by selecting a
nouns from a 2D diagram (like sail plan) and from a drop
down menu selecting a verb.
