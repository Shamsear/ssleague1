// Socket.IO client for real-time updates
let socket;
let connectedToSocket = false;
let currentAuctionRound = null;

// Initialize the Socket.IO connection
function initSocket() {
  // Connect to the Socket.IO server
  socket = io();
  
  // Connection events
  socket.on('connect', handleSocketConnect);
  socket.on('disconnect', handleSocketDisconnect);
  
  // Notification events
  socket.on('connection_status', handleConnectionStatus);
  socket.on('personal_notification', handlePersonalNotification);
  
  // Auction events
  socket.on('round_start', handleRoundStart);
  socket.on('round_end', handleRoundEnd);
  socket.on('auction_update', handleAuctionUpdate);
  socket.on('auction_message', handleAuctionMessage);
  socket.on('tiebreaker_start', handleTiebreakerStart);
  socket.on('tiebreaker_end', handleTiebreakerEnd);
  socket.on('player_allocated', handlePlayerAllocated);
  
  // Admin-specific events
  socket.on('admin_notification', handleAdminNotification);
  socket.on('admin_update', handleAdminUpdate);
}

// Join an auction round room to receive updates
function joinAuctionRoom(roundId) {
  if (!socket || !connectedToSocket) return;
  
  currentAuctionRound = roundId;
  socket.emit('join_auction', { round_id: roundId });
  console.log(`Joined auction room for round ${roundId}`);
}

// Leave an auction round room
function leaveAuctionRoom(roundId) {
  if (!socket || !connectedToSocket) return;
  
  socket.emit('leave_auction', { round_id: roundId });
  currentAuctionRound = null;
  console.log(`Left auction room for round ${roundId}`);
}

// Event Handlers
function handleSocketConnect() {
  console.log('Connected to real-time updates');
  connectedToSocket = true;
  showConnectionStatus('Connected', 'success');
  
  // If there's an active auction, join its room
  const roundIdElement = document.getElementById('active-round-id');
  if (roundIdElement && roundIdElement.value) {
    joinAuctionRoom(roundIdElement.value);
  }
}

function handleSocketDisconnect() {
  console.log('Disconnected from real-time updates');
  connectedToSocket = false;
  showConnectionStatus('Disconnected', 'error');
}

function handleConnectionStatus(data) {
  console.log('Connection status:', data);
  if (data.status === 'connected') {
    showConnectionStatus('Connected', 'success');
  }
}

function handleRoundStart(data) {
  console.log('New auction round started:', data);
  
  // Update UI to show new round
  showNotification('New Auction Round', `A new round for ${data.position} players has started!`, 'info');
  
  // If on dashboard, refresh to show updated round
  if (window.location.pathname.includes('dashboard')) {
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  }
}

function handleRoundEnd(data) {
  console.log('Auction round ended:', data);
  
  // Update UI to show round ended
  showNotification('Auction Round Ended', `The round for ${data.position} players has ended.`, 'info');
  
  // If viewing this round, refresh to show results
  if (currentAuctionRound === data.round_id) {
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  }
}

function handleAuctionUpdate(data) {
  console.log('Auction update:', data);
  
  // Update UI elements for real-time auction state
  updateAuctionUI(data);
}

function handleAuctionMessage(data) {
  console.log('Auction message:', data);
  showNotification('Auction Update', data.message, 'info');
}

function handleTiebreakerStart(data) {
  console.log('Tiebreaker started:', data);
  showNotification('Tiebreaker Started', `A tiebreaker for ${data.player_name} has started!`, 'warning');
  
  // If user is involved in this tiebreaker, suggest redirecting
  if (data.teams && data.teams.includes(getUserTeamId())) {
    if (confirm('You are involved in a tiebreaker! Go to tiebreaker page?')) {
      window.location.href = `/team/tiebreaker/${data.round_id}`;
    }
  }
}

function handleTiebreakerEnd(data) {
  console.log('Tiebreaker ended:', data);
  showNotification('Tiebreaker Ended', `The tiebreaker for ${data.player_name} has ended.`, 'info');
  
  // If viewing this tiebreaker, refresh to show results
  if (currentAuctionRound === data.round_id) {
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  }
}

function handlePlayerAllocated(data) {
  console.log('Player allocated:', data);
  showNotification('Player Allocated', `${data.player_name} was allocated to ${data.team_name}!`, 'success');
  
  // If on team players page, refresh to show new player
  if (window.location.pathname.includes('team/players')) {
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  }
}

function handlePersonalNotification(data) {
  console.log('Personal notification:', data);
  showNotification(data.title || 'Notification', data.message, data.type || 'info');
}

function handleAdminNotification(data) {
  // Only process if user is admin
  if (!isUserAdmin()) return;
  
  console.log('Admin notification:', data);
  
  // Update admin UI
  const adminLogElement = document.getElementById('admin-activity-log');
  if (adminLogElement) {
    const timestamp = new Date().toLocaleTimeString();
    const logItem = document.createElement('div');
    logItem.className = 'p-2 border-b border-gray-200';
    logItem.innerHTML = `<span class="text-gray-500">${timestamp}</span> ${data.message}`;
    adminLogElement.prepend(logItem);
    
    // Keep only the most recent 50 items
    const items = adminLogElement.children;
    if (items.length > 50) {
      adminLogElement.removeChild(items[items.length - 1]);
    }
  }
}

function handleAdminUpdate(data) {
  // Only process if user is admin
  if (!isUserAdmin()) return;
  
  console.log('Admin update:', data);
  
  // Update admin real-time info
  if (data.type === 'new_bid') {
    showNotification('New Bid', `${data.team_name} bid ${data.amount} on a player`, 'info');
    updateAdminBidLog(data);
  } else if (data.type === 'tiebreaker_bid') {
    showNotification('Tiebreaker Bid', `${data.team_name} placed a tiebreaker bid of ${data.amount}`, 'warning');
    updateAdminTiebreakerLog(data);
  }
}

// Helper functions

function getUserTeamId() {
  const teamIdElement = document.getElementById('user-team-id');
  return teamIdElement ? teamIdElement.value : null;
}

function isUserAdmin() {
  const userRoleElement = document.getElementById('user-role');
  return userRoleElement && userRoleElement.value === 'admin';
}

function showConnectionStatus(status, type) {
  const statusElement = document.getElementById('connection-status');
  if (!statusElement) return;
  
  statusElement.textContent = status;
  statusElement.className = type === 'success' 
    ? 'text-green-500 font-medium'
    : 'text-red-500 font-medium';
}

function showNotification(title, message, type) {
  // Check if we have a notification container
  const container = document.getElementById('notification-container');
  if (!container) return;
  
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `glass px-4 py-3 rounded-xl mb-3 animate__animated animate__fadeIn ${type === 'error' ? 'border-red-300' : type === 'warning' ? 'border-yellow-300' : type === 'success' ? 'border-green-300' : 'border-blue-300'}`;
  
  notification.innerHTML = `
    <div class="flex items-start">
      <div class="flex-shrink-0 mt-0.5">
        <svg class="w-5 h-5 ${type === 'error' ? 'text-red-500' : type === 'warning' ? 'text-yellow-500' : type === 'success' ? 'text-green-500' : 'text-blue-500'}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${type === 'error' ? 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' : type === 'warning' ? 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' : type === 'success' ? 'M5 13l4 4L19 7' : 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'}"></path>
        </svg>
      </div>
      <div class="ml-3 w-0 flex-1">
        <h3 class="text-sm font-medium">${title}</h3>
        <div class="mt-1 text-sm text-gray-500">${message}</div>
      </div>
      <div class="ml-4 flex-shrink-0 flex">
        <button class="inline-flex text-gray-400 hover:text-gray-500" onclick="this.parentElement.parentElement.parentElement.remove()">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
    </div>
  `;
  
  // Add to container
  container.prepend(notification);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    notification.classList.add('animate__fadeOut');
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 500);
  }, 5000);
}

function updateAuctionUI(data) {
  // Update timer if available
  if (data.timer) {
    const timerElement = document.getElementById('auction-timer');
    if (timerElement) {
      timerElement.textContent = data.timer;
    }
  }
  
  // Update any other auction UI elements
  // This would be specific to the application's UI
}

function updateAdminBidLog(data) {
  const logElement = document.getElementById('admin-bid-log');
  if (!logElement) return;
  
  const logItem = document.createElement('div');
  logItem.className = 'p-2 border-b border-gray-200';
  
  const timestamp = new Date(data.timestamp).toLocaleTimeString();
  logItem.innerHTML = `
    <span class="text-gray-500">${timestamp}</span>
    <span class="font-medium">${data.team_name}</span> bid
    <span class="font-medium">${data.amount}</span> coins
    <span class="text-gray-500">in round ${data.round_id}</span>
  `;
  
  logElement.prepend(logItem);
  
  // Keep only the most recent 50 items
  const items = logElement.children;
  if (items.length > 50) {
    logElement.removeChild(items[items.length - 1]);
  }
}

function updateAdminTiebreakerLog(data) {
  const logElement = document.getElementById('admin-tiebreaker-log');
  if (!logElement) return;
  
  const logItem = document.createElement('div');
  logItem.className = 'p-2 border-b border-gray-200';
  
  const timestamp = new Date(data.timestamp).toLocaleTimeString();
  logItem.innerHTML = `
    <span class="text-gray-500">${timestamp}</span>
    <span class="font-medium">${data.team_name}</span> tiebreaker bid
    <span class="font-medium">${data.amount}</span> coins
    <span class="text-gray-500">in round ${data.round_id}</span>
  `;
  
  logElement.prepend(logItem);
  
  // Keep only the most recent 50 items
  const items = logElement.children;
  if (items.length > 50) {
    logElement.removeChild(items[items.length - 1]);
  }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
  // Only initialize if we have required DOM elements
  if (!document.getElementById('notification-container')) {
    console.log('Not initializing Socket.IO client - required elements missing');
    return;
  }
  
  console.log('Initializing Socket.IO client for real-time updates');
  initSocket();
  
  // Add real-time status indicator
  const notificationContainer = document.getElementById('notification-container');
  if (notificationContainer) {
    const statusElement = document.createElement('div');
    statusElement.className = 'text-xs mt-1';
    statusElement.innerHTML = `
      <span class="font-medium">Real-time updates:</span>
      <span id="connection-status" class="text-gray-500">Connecting...</span>
    `;
    
    // Add after the first child of the container
    if (notificationContainer.firstChild) {
      notificationContainer.firstChild.appendChild(statusElement);
    } else {
      notificationContainer.appendChild(statusElement);
    }
  }
}); 