/**
 * Real-time Seat Selection Manager
 * Handles temporary seat selection, real-time updates, and seat status display
 */
class RealTimeSeatManager {
    constructor(scheduleId, userId) {
        this.scheduleId = scheduleId;
        this.userId = userId;
        this.updateInterval = null;
        this.selectedSeats = new Set();
        this.tempSelections = new Map(); // seat_number -> selection_info
        this.bookedSeats = new Set();
        this.availableSeats = new Set();
        this.isInitialized = false;
        
        // Initialize CSRF token
        this.csrfToken = this.getCSRFToken();
        
        // Bind methods
        this.handleSeatClick = this.handleSeatClick.bind(this);
        this.updateSeatDisplay = this.updateSeatDisplay.bind(this);
        this.startRealTimeUpdates = this.startRealTimeUpdates.bind(this);
        this.stopRealTimeUpdates = this.stopRealTimeUpdates.bind(this);
    }
    
    /**
     * Get CSRF token from cookies
     */
    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    /**
     * Initialize the seat manager
     */
    async initialize() {
        try {
            // Get initial seat status
            await this.fetchSeatStatus();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Start real-time updates
            this.startRealTimeUpdates();
            
            this.isInitialized = true;
            console.log('Real-time seat manager initialized');
            
        } catch (error) {
            console.error('Failed to initialize seat manager:', error);
        }
    }
    
    /**
     * Set up event listeners for seat interactions
     */
    setupEventListeners() {
        // Add click handlers to all seats
        const seats = document.querySelectorAll('.seat[data-seat-number]');
        seats.forEach(seat => {
            seat.addEventListener('click', this.handleSeatClick);
        });
        
        // Add window focus/blur handlers for real-time updates
        window.addEventListener('focus', () => this.startRealTimeUpdates());
        window.addEventListener('blur', () => this.stopRealTimeUpdates());
        
        // Add page visibility change handler
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopRealTimeUpdates();
            } else {
                this.startRealTimeUpdates();
            }
        });
    }
    
    /**
     * Handle seat click events
     */
    async handleSeatClick(event) {
        const seat = event.target;
        const seatNumber = parseInt(seat.dataset.seatNumber);
        const status = seat.dataset.status;
        
        if (status === 'booked') {
            return; // Cannot interact with booked seats
        }
        
        if (status === 'temporary' && seat.dataset.userId == this.userId) {
            // User is deselecting their own temporary selection
            await this.deselectSeat(seatNumber);
        } else if (status === 'available') {
            // User is selecting an available seat
            await this.selectSeat(seatNumber);
        }
    }
    
    /**
     * Temporarily select a seat
     */
    async selectSeat(seatNumber) {
        try {
            const response = await fetch('/api/temporary-selections/select_seat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                },
                body: JSON.stringify({
                    schedule_id: this.scheduleId,
                    seat_number: seatNumber
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.selectedSeats.add(seatNumber);
                await this.fetchSeatStatus(); // Refresh seat status
                this.showNotification(`Seat ${seatNumber} temporarily selected`, 'success');
            } else {
                this.showNotification(data.error || 'Failed to select seat', 'error');
            }
            
        } catch (error) {
            console.error('Error selecting seat:', error);
            this.showNotification('Failed to select seat. Please try again.', 'error');
        }
    }
    
    /**
     * Remove temporary seat selection
     */
    async deselectSeat(seatNumber) {
        try {
            const response = await fetch('/api/temporary-selections/deselect_seat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                },
                body: JSON.stringify({
                    schedule_id: this.scheduleId,
                    seat_number: seatNumber
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.selectedSeats.delete(seatNumber);
                await this.fetchSeatStatus(); // Refresh seat status
                this.showNotification(`Seat ${seatNumber} deselected`, 'success');
            } else {
                this.showNotification(data.message || 'Failed to deselect seat', 'error');
            }
            
        } catch (error) {
            console.error('Error deselecting seat:', error);
            this.showNotification('Failed to deselect seat. Please try again.', 'error');
        }
    }
    
    /**
     * Fetch current seat status from the server
     */
    async fetchSeatStatus() {
        try {
            const response = await fetch(`/api/schedules/${this.scheduleId}/seat_status/`, {
                headers: {
                    'X-CSRFToken': this.csrfToken,
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // Update internal state
            this.bookedSeats = new Set(data.booked_seats);
            this.availableSeats = new Set(data.available_seats);
            this.tempSelections = new Map();
            
            // Convert temporary selections to Map
            Object.entries(data.temporary_selections).forEach(([seatNum, info]) => {
                this.tempSelections.set(parseInt(seatNum), info);
            });
            
            // Update display
            this.updateSeatDisplay();
            
        } catch (error) {
            console.error('Error fetching seat status:', error);
        }
    }
    
    /**
     * Update the visual display of seats
     */
    updateSeatDisplay() {
        const seats = document.querySelectorAll('.seat[data-seat-number]');
        
        seats.forEach(seat => {
            const seatNumber = parseInt(seat.dataset.seatNumber);
            
            // Remove all status classes
            seat.classList.remove('bg-gray-200', 'bg-red-400', 'bg-yellow-400', 'bg-green-500', 'text-white');
            seat.classList.remove('hover:bg-gray-300', 'cursor-not-allowed', 'cursor-pointer');
            
            // Reset dataset
            seat.dataset.status = 'available';
            delete seat.dataset.userId;
            delete seat.dataset.username;
            
            if (this.bookedSeats.has(seatNumber)) {
                // Booked seat
                seat.classList.add('bg-red-400', 'text-white', 'cursor-not-allowed');
                seat.dataset.status = 'booked';
                seat.title = 'Booked';
                
            } else if (this.tempSelections.has(seatNumber)) {
                // Temporarily selected seat
                const selection = this.tempSelections.get(seatNumber);
                seat.classList.add('bg-yellow-400', 'text-white', 'cursor-not-allowed');
                seat.dataset.status = 'temporary';
                seat.dataset.userId = selection.user_id;
                seat.dataset.username = selection.username;
                
                if (selection.user_id == this.userId) {
                    // User's own selection
                    seat.classList.remove('bg-yellow-400');
                    seat.classList.add('bg-green-500');
                    seat.classList.add('cursor-pointer');
                    seat.title = `Your selection (expires in ${this.getTimeUntilExpiry(selection.expires_at)})`;
                } else {
                    // Another user's selection
                    seat.title = `Temporarily selected by ${selection.username} (expires in ${this.getTimeUntilExpiry(selection.expires_at)})`;
                }
                
            } else {
                // Available seat
                seat.classList.add('bg-gray-200', 'hover:bg-gray-300', 'cursor-pointer');
                seat.title = 'Available';
            }
        });
        
        // Update legend
        this.updateLegend();
    }
    
    /**
     * Update the seat legend to show temporary selections
     */
    updateLegend() {
        const legendContainer = document.querySelector('.seat-legend');
        if (!legendContainer) return;
        
        // Add temporary selection legend if not exists
        let tempLegend = legendContainer.querySelector('.temp-legend');
        if (!tempLegend) {
            tempLegend = document.createElement('div');
            tempLegend.className = 'temp-legend flex items-center mr-4';
            tempLegend.innerHTML = '<span class="w-4 h-4 bg-yellow-400 rounded-sm inline-block mr-2"></span> Temporarily Selected';
            legendContainer.appendChild(tempLegend);
        }
        
        // Add user's own selection legend if not exists
        let ownLegend = legendContainer.querySelector('.own-legend');
        if (!ownLegend) {
            ownLegend = document.createElement('div');
            ownLegend.className = 'own-legend flex items-center mr-4';
            ownLegend.innerHTML = '<span class="w-4 h-4 bg-green-500 rounded-sm inline-block mr-2"></span> Your Selection';
            legendContainer.appendChild(ownLegend);
        }
    }
    
    /**
     * Calculate time until expiry
     */
    getTimeUntilExpiry(expiresAt) {
        const now = new Date();
        const expiry = new Date(expiresAt);
        const diffMs = expiry - now;
        
        if (diffMs <= 0) return 'expired';
        
        const diffMins = Math.ceil(diffMs / (1000 * 60));
        return `${diffMins} min${diffMins !== 1 ? 's' : ''}`;
    }
    
    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        if (this.updateInterval) return;
        
        this.updateInterval = setInterval(async () => {
            await this.fetchSeatStatus();
        }, 5000); // Update every 5 seconds
        
        console.log('Real-time updates started');
    }
    
    /**
     * Stop real-time updates
     */
    stopRealTimeUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
            console.log('Real-time updates stopped');
        }
    }
    
    /**
     * Show notification to user
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-sm ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }
    
    /**
     * Clean up resources
     */
    destroy() {
        this.stopRealTimeUpdates();
        
        // Remove event listeners
        const seats = document.querySelectorAll('.seat[data-seat-number]');
        seats.forEach(seat => {
            seat.removeEventListener('click', this.handleSeatClick);
        });
        
        window.removeEventListener('focus', this.startRealTimeUpdates);
        window.removeEventListener('blur', this.stopRealTimeUpdates);
        document.removeEventListener('visibilitychange', this.startRealTimeUpdates);
        
        console.log('Real-time seat manager destroyed');
    }
}

/**
 * Initialize real-time seat management when the page loads
 */
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a booking page with schedule ID
    const scheduleIdElement = document.querySelector('input[name="schedule_id"]');
    const userIdElement = document.querySelector('meta[name="user-id"]');
    
    if (scheduleIdElement && userIdElement) {
        const scheduleId = scheduleIdElement.value;
        const userId = userIdElement.content;
        
        // Initialize the real-time seat manager
        window.seatManager = new RealTimeSeatManager(scheduleId, userId);
        window.seatManager.initialize();
        
        // Clean up on page unload
        window.addEventListener('beforeunload', () => {
            if (window.seatManager) {
                window.seatManager.destroy();
            }
        });
    }
}); 