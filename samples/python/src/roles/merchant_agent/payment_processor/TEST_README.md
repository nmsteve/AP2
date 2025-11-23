# Testing initiate_payment Function

This directory contains test files for the `initiate_payment` function with mock data.

## Files

- **`test_tools.py`**: Contains comprehensive test cases with mock data
- **`run_test.py`**: Simple test runner script

## Test Cases

The test suite includes the following scenarios:

1. **Missing Payment Mandate**: Tests error handling when no payment mandate is provided
2. **Card Payment - First Call**: Tests the OTP challenge flow for card payments
3. **Card Payment - Valid Challenge**: Tests successful payment with correct OTP (123)
4. **Card Payment - Invalid Challenge**: Tests rejection of incorrect OTP
5. **SOHO Credit Payment**: Tests biometric authentication flow (skips OTP)

## Running Tests

### Run all tests:
```bash
cd /home/steve/Documents/AP2/samples/python/src/roles/merchant_agent/payment_processor
python test_tools.py
```

Or using the runner:
```bash
python run_test.py
```

### Run a specific test:
```bash
python run_test.py missing              # Test missing mandate
python run_test.py card_first           # Test card payment first call
python run_test.py valid_challenge      # Test valid OTP
python run_test.py invalid_challenge    # Test invalid OTP
python run_test.py soho                 # Test SOHO credit payment
```

## Mock Data Structure

### Payment Mandate
```python
{
    "payment_mandate_contents": {
        "payment_mandate_id": "unique-uuid",
        "timestamp": "ISO-8601 timestamp",
        "payment_details_total": {
            "amount": "100.00",
            "currency": "USD"
        },
        "payment_response": {
            "method_name": "CARD",  # or "SOHO_CREDIT"
            "details": {
                "token": {
                    "provider_url": "http://localhost:8002",
                    "token_value": "test_token_12345"
                },
                "last4": "1234",
                "brand": "Visa"
            }
        }
    }
}
```

### Data Parts
```python
[
    {
        "key": "ap2.mandates.PaymentMandate",
        "value": <payment_mandate>
    },
    {
        "key": "challenge_response",
        "value": "123"  # Valid OTP for testing
    }
]
```

## Customizing Tests

You can modify the mock data by editing the helper functions in `test_tools.py`:

- `create_mock_payment_mandate()`: Customize payment mandate structure
- `create_mock_data_parts()`: Control which data parts are included
- `create_mock_updater()`: Modify TaskUpdater behavior
- `create_mock_task()`: Adjust task state and properties

## Dependencies

The tests use Python's built-in `unittest.mock` module and don't require additional testing frameworks. Make sure you have the AP2 dependencies installed:

```bash
pip install -e /home/steve/Documents/AP2
```
