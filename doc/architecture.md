This is currently in prototype mode, and is not designed for large scale.  We’ll use a model with clients connecting to an authoritative server that maintains game state.  The clients will send moves to the server, and receive state updates that they display locally to the user.  The server supports multiple games, denoted by unique IDs.  

### Server

The server will be implemented using Flask and all state is in-memory within the Flask process.  Once a game is started, each client will have a bidirectional Websocket connection to the server used to send moves and receive updates.

Each game is *mostly* event-driven, in that it responds to player moves and sends back state.  However, given that the state can also progress independently (turns can end after a time limit elapses) we'll also need some sort of timer mechanism per game to tick the clock and possibly make updates as a result.

