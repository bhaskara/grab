This document contains the high level requirements for the game I’m trying to build, which is a web-based version of a game called “Grab”, that is often played with Scrabble tiles.

### How the physical game is played

There is a set of players who have a bag of Scrabble tiles.  There is a central area which we’ll call the pool.  Additionally each player has a dedicated area in front of them.  At any point during the game, each player has a set of words in their area (made out of tiles), and there are a set of tiles face up in the pool (initially, both the player areas and the pool are empty, as all the tiles are in the bag).  At the beginning of each turn, a tile is randomly selected from the bag and added to the pool.  Then, any player may form a word by selecting one or more existing words from the various player areas, and one or more tiles from the pool, and combining those all into a new word.  They then place that word in front of them.  At this point, their score is increased by the sum of the points on each Scrabble tile in their word.  An illegal word attempt is treated as a no-op.  This process continues until no player is able to form new words as described, or until a time limit elapses.  Then a new turn happens (by randomly selecting a new tile).  The game ends when all tiles run out, at which point each player gets an additional bonus equalling the score of all the words in their area.

### How the online gameplay would work

I’m envisioning that a set of players join a game (using some TBD mechanism) from their client (assume a web browser for now).  Each player sees the game state and can form words by typing them and hitting enter.  Assuming the word can be legally played using the mechanism described above, the game will then make the word for them and update the state accordingly for all players.  There’ll be some mechanism for all players to indicate that they can’t make any more words, and then the next turn will happen.  

The players may be in different locations from each other and from any server.  It should have reasonably low latency, e.g., if one player makes a move, then that should reflect in other players state within a few hundred ms, to avoid perceived race conditions.

### Games, users, etc.

The flow would be:

1. Players browse to the game URL and enter their name to log in.
2. A first user clicks a “new game” button somewhere.
3. This starts a new game and displays an ID.
4. Other players connect to a URL based on that ID.
5. The first player clicks “start game” and the game begins.

