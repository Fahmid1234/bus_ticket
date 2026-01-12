from django.conf import settings
import requests
import json
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def initiate_payment(booking):
    """
    Initiate SSLCOMMERZ payment for a booking
    """
    try:
        # Calculate total amount
        total_amount = float(booking.seats_booked * booking.schedule.fare)
        
        # Create unique transaction ID
        transaction_id = f'BUS_TICKET_{booking.id}_{booking.booking_time.strftime("%Y%m%d%H%M%S")}'
        
        # Prepare the payment data
        post_data = {
            'store_id': settings.STORE_ID,
            'store_passwd': settings.STORE_PASSWORD,
            'total_amount': total_amount,
            'currency': 'BDT',
            'tran_id': transaction_id,
            'success_url': 'http://127.0.0.1:8000/payment-success/',
            'fail_url': 'http://127.0.0.1:8000/payment-fail/',
            'cancel_url': 'http://127.0.0.1:8000/payment-cancel/',
            'ipn_url': 'http://127.0.0.1:8000/payment-ipn/',
            'cus_name': booking.passenger_name,
            'cus_email': booking.passenger_email,
            'cus_phone': booking.passenger_phone,
            'cus_add1': 'Not Provided',
            'cus_city': 'Not Provided',
            'cus_country': 'Bangladesh',
            'shipping_method': 'NO',
            'product_name': f'Bus Ticket - {booking.schedule.route}',
            'product_category': 'Transport',
            'product_profile': 'non-physical-goods',
        }

        logger.info(f"Initiating payment for booking {booking.id} with transaction ID {transaction_id}")
        logger.debug(f"Payment request data: {json.dumps(post_data, indent=2)}")

        # Make the API request
        response = requests.post(
            'https://sandbox.sslcommerz.com/gwprocess/v4/api.php',
            data=post_data,
            verify=True,
            timeout=30
        )

        # Log the response
        logger.debug(f"SSLCOMMERZ API Response: {response.text}")

        if response.status_code == 200:
            try:
                response_data = response.json()
                
                # Check for specific error messages in the response
                if response_data.get('status') == 'FAILED':
                    error_reason = response_data.get('failedreason') or response_data.get('message')
                    logger.error(f"Payment initiation failed: {error_reason}")
                    return {
                        'status': 'FAILED',
                        'message': f"SSLCOMMERZ Error: {error_reason}"
                    }
                
                # If successful, return the response data
                if response_data.get('status') == 'SUCCESS':
                    logger.info(f"Payment initiation successful for booking {booking.id}")
                    return response_data
                
                # If neither success nor failed, something unexpected happened
                logger.error(f"Unexpected response status: {response_data.get('status')}")
                return {
                    'status': 'FAILED',
                    'message': 'Unexpected response from payment gateway'
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse SSLCOMMERZ response: {str(e)}")
                return {
                    'status': 'FAILED',
                    'message': 'Invalid response from payment gateway'
                }
        else:
            logger.error(f"HTTP {response.status_code} error from SSLCOMMERZ API")
            return {
                'status': 'FAILED',
                'message': f'Payment gateway returned status code {response.status_code}'
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during payment initiation: {str(e)}")
        return {
            'status': 'FAILED',
            'message': 'Could not connect to payment gateway. Please try again.'
        }
    except Exception as e:
        logger.error(f"Unexpected error during payment initiation: {str(e)}")
        return {
            'status': 'FAILED',
            'message': 'An unexpected error occurred. Please try again.'
        }

def verify_payment(post_data):
    """
    Verify SSLCOMMERZ payment response
    """
    try:
        # Log the verification request
        logger.info("Verifying payment response")
        logger.debug(f"Verification data: {json.dumps(post_data, indent=2)}")

        # Extract verification data
        verify_sign = post_data.get('verify_sign')
        verify_key = post_data.get('verify_key')
        tran_id = post_data.get('tran_id', '')
        amount = post_data.get('amount')
        status = post_data.get('status')
        
        # Verify the transaction
        if status == 'VALID' and verify_sign and verify_key:
            try:
                # Extract booking ID from transaction ID
                booking_id = tran_id.split('_')[2]  # Format: BUS_TICKET_ID_TIMESTAMP
                logger.info(f"Payment verification successful for booking {booking_id}")
                return True, booking_id
            except IndexError:
                logger.error(f"Invalid transaction ID format: {tran_id}")
                return False, None
        
        logger.warning(f"Payment verification failed. Status: {status}")
        return False, None

    except Exception as e:
        logger.error(f"Error during payment verification: {str(e)}")
        return False, None 