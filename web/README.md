# Grab Game Web Frontend

This is a React web frontend for the Grab word game server.

## Step 1: React Setup + Socket.IO - COMPLETED ✅

### What was implemented:
1. ✅ Created React app in the `web/` directory
2. ✅ Installed Socket.IO client library (socket.io-client@4.8.1)
3. ✅ Set up basic React app structure with Socket.IO integration
4. ✅ Created test interface to verify Socket.IO connection

### Testing Step 1:

1. **Basic React app runs:**
   ```bash
   cd web
   npm start
   # Should see React app at http://localhost:3000
   ```

2. **Socket.IO client library installed:**
   ```bash
   npm list socket.io-client
   # Shows: socket.io-client@4.8.1
   ```

3. **Test Socket.IO connection to server:**
   - Start your Grab game server first: `python run.py` (from root directory)
   - Open browser to http://localhost:3000
   - Click "Test Socket.IO Connection" button
   - Should see connection status change to "Connected" if server is running

### Success Criteria (Step 1):
- ✅ React dev server starts without errors
- ✅ Browser console shows no import errors
- ✅ App builds successfully with `npm run build`
- ✅ Socket.IO connection can be established to server at localhost:5000

### Next Steps:
Ready for Step 2: Authentication + Socket Connection

### Files Created/Modified:
- `src/App.js` - Main app component with Socket.IO connection test
- `package.json` - Added socket.io-client dependency
- This README.md

### Browser Console Testing:
You can also test the Socket.IO connection manually in browser console:
```javascript
import('socket.io-client').then(({default: io}) => {
  const socket = io('http://localhost:5000');
  socket.on('connect', () => console.log('Connected!'));
  socket.on('disconnect', () => console.log('Disconnected'));
});
```

---

# Original Create React App Documentation

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
