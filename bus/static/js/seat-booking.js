/**
 * Seat Booking Utility for Bus Ticketing System
 * Handles real-time seat availability checking and booking to prevent race conditions
 */

class SeatBookingManager {
    constructor() {
        this.csrfToken = this.getCSRFToken();
        this.availabilityCache = new Map();
        this.bookingInProgress = false;
        this.refreshInterval = null;
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
     * Start real-time seat availability monitoring
     */
    startAvailabilityMonitoring(scheduleId, updateCallback) {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        // Initial check
        this.checkSeatAvailability(scheduleId, updateCallback);

        // Set up periodic refresh (every 5 seconds)
        this.refreshInterval = setInterval(() => {
            this.checkSeatAvailability(scheduleId, updateCallback);
        }, 5000);

        return this.refreshInterval;
    }

    /**
     * Stop availability monitoring
     */
    stopAvailabilityMonitoring() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Check seat availability for a specific schedule
     */
    async checkSeatAvailability(scheduleId, callback) {
        try {
            const response = await fetch(`/api/schedules/${scheduleId}/seat_availability/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Cache the result
            this.availabilityCache.set(scheduleId, {
                data: data,
                timestamp: Date.now()
            });

            if (callback) {
                callback(data);
            }

            return data;
        } catch (error) {
            console.error('Error checking seat availability:', error);
            return null;
        }
    }

    /**
     * Check if specific seats are available
     */
    async checkSpecificSeats(scheduleId, seatNumbers, callback) {
        try {
            const response = await fetch(`/api/schedules/${scheduleId}/check_seats/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    seat_numbers: seatNumbers
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (callback) {
                callback(data);
            }

            return data;
        } catch (error) {
            console.error('Error checking specific seats:', error);
            return null;
        }
    }

    /**
     * Book seats with transaction-based locking
     */
    async bookSeats(bookingData, callback) {
        if (this.bookingInProgress) {
            throw new Error('Booking already in progress. Please wait.');
        }

        this.bookingInProgress = true;

        try {
            const response = await fetch('/api/bookings/book_seats/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify(bookingData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Booking failed');
            }

            const data = await response.json();
            
            // Clear availability cache for this schedule
            this.availabilityCache.delete(bookingData.schedule_id);
            
            if (callback) {
                callback(data);
            }

            return data;
        } catch (error) {
            console.error('Error booking seats:', error);
            throw error;
        } finally {
            this.bookingInProgress = false;
        }
    }

    /**
     * Cancel a booking
     */
    async cancelBooking(bookingId, callback) {
        try {
            const response = await fetch(`/api/bookings/${bookingId}/cancel_booking/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Cancellation failed');
            }

            const data = await response.json();
            
            if (callback) {
                callback(data);
            }

            return data;
        } catch (error) {
            console.error('Error cancelling booking:', error);
            throw error;
        }
    }

    /**
     * Get cached availability data
     */
    getCachedAvailability(scheduleId) {
        const cached = this.availabilityCache.get(scheduleId);
        if (cached && (Date.now() - cached.timestamp) < 10000) { // 10 second cache
            return cached.data;
        }
        return null;
    }

    /**
     * Clear availability cache
     */
    clearCache(scheduleId = null) {
        if (scheduleId) {
            this.availabilityCache.delete(scheduleId);
        } else {
            this.availabilityCache.clear();
        }
    }
}

/**
 * Seat Selection Handler for the booking form
 */
class SeatSelectionHandler {
    constructor(container, maxSeats = 4) {
        this.container = container;
        this.maxSeats = maxSeats;
        this.selectedSeats = new Set();
        this.bookingManager = new SeatBookingManager();
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateSelectionDisplay();
    }

    bindEvents() {
        // Handle seat clicks
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('seat')) {
                this.toggleSeat(e.target);
            }
        });

        // Handle form submission
        const form = this.container.closest('form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleFormSubmission(form);
            });
        }
    }

    toggleSeat(seatElement) {
        const seatNumber = parseInt(seatElement.dataset.seat);
        
        if (this.selectedSeats.has(seatNumber)) {
            // Deselect seat
            this.selectedSeats.delete(seatNumber);
            seatElement.classList.remove('selected');
        } else {
            // Check if we can select more seats
            if (this.selectedSeats.size >= this.maxSeats) {
                alert(`You can only select up to ${this.maxSeats} seats.`);
                return;
            }
            
            // Select seat
            this.selectedSeats.add(seatNumber);
            seatElement.classList.add('selected');
        }
        
        this.updateSelectionDisplay();
    }

    updateSelectionDisplay() {
        const display = this.container.querySelector('.seat-selection-display');
        if (display) {
            const selectedArray = Array.from(this.selectedSeats).sort((a, b) => a - b);
            display.textContent = `Selected seats: ${selectedArray.join(', ')} (${this.selectedSeats.size}/${this.maxSeats})`;
        }
    }

    async handleFormSubmission(form) {
        const scheduleId = form.querySelector('[name="schedule_id"]')?.value;
        const passengerName = form.querySelector('[name="name"]')?.value;
        const passengerEmail = form.querySelector('[name="email"]')?.value;
        const passengerPhone = form.querySelector('[name="phone"]')?.value;

        if (!scheduleId || !passengerName || !passengerEmail || !passengerPhone) {
            alert('Please fill in all required fields.');
            return;
        }

        if (this.selectedSeats.size === 0) {
            alert('Please select at least one seat.');
            return;
        }

        // Check seat availability one more time before booking
        try {
            const seatCheck = await this.bookingManager.checkSpecificSeats(
                scheduleId, 
                Array.from(this.selectedSeats)
            );

            if (!seatCheck.all_available) {
                alert(`Seats ${seatCheck.unavailable_seats.join(', ')} are no longer available. Please select different seats.`);
                this.refreshSeatDisplay();
                return;
            }

            // Proceed with booking
            const bookingData = {
                schedule_id: parseInt(scheduleId),
                passenger_name: passengerName,
                passenger_email: passengerEmail,
                passenger_phone: passengerPhone,
                seat_numbers: Array.from(this.selectedSeats)
            };

            const result = await this.bookingManager.bookSeats(bookingData);
            
            if (result.success) {
                // Redirect to payment page
                window.location.href = `/payment/${result.booking_id}/`;
            }
        } catch (error) {
            alert(`Booking failed: ${error.message}`);
            this.refreshSeatDisplay();
        }
    }

    refreshSeatDisplay() {
        // Refresh the seat display to show current availability
        const scheduleId = this.container.querySelector('[name="schedule_id"]')?.value;
        if (scheduleId) {
            this.bookingManager.checkSeatAvailability(scheduleId, (data) => {
                this.updateSeatDisplay(data);
            });
        }
    }

    updateSeatDisplay(availabilityData) {
        // Update seat display based on availability
        const seats = this.container.querySelectorAll('.seat');
        seats.forEach(seat => {
            const seatNumber = parseInt(seat.dataset.seat);
            if (availabilityData.booked_seats.includes(seatNumber)) {
                seat.classList.add('booked');
                seat.classList.remove('available', 'selected');
            } else {
                seat.classList.add('available');
                seat.classList.remove('booked');
            }
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize seat selection handler if booking form exists
    const bookingContainer = document.querySelector('.seat-selection-container');
    if (bookingContainer) {
        new SeatSelectionHandler(bookingContainer);
    }

    // Initialize availability monitoring for schedule pages
    const scheduleId = document.querySelector('[data-schedule-id]')?.dataset.scheduleId;
    if (scheduleId) {
        const bookingManager = new SeatBookingManager();
        bookingManager.startAvailabilityMonitoring(scheduleId, (data) => {
            // Update availability display
            updateAvailabilityDisplay(data);
        });
    }
});

/**
 * Update availability display on schedule pages
 */
function updateAvailabilityDisplay(availabilityData) {
    const availabilityElement = document.querySelector('.availability-display');
    if (availabilityElement) {
        availabilityElement.innerHTML = `
            <strong>Available Seats:</strong> ${availabilityData.available_count}/${availabilityData.total_seats}
            <br>
            <small>Last updated: ${new Date().toLocaleTimeString()}</small>
        `;
    }
} 