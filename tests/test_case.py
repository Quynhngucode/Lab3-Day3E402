"""
Test cases for Movie Ticket Booking Agent

These test cases are based on the following mock data:
- Movies: Dune: Part Two, The Batman, Spider-Man: Across the Spider-Verse
- Seat types: Standard, VIP
- Vouchers: CGV30, STUDENT, HELLOSUMMER
- Concessions: popcorn_combo_1, popcorn_combo_2

Each test case includes:
- id: test case ID
- category: what type of behavior is being tested
- user_input: natural language input in English
- expected_behavior: what the agent should do
- expected_tools: tools expected to be called in order
- expected_result: high-level expected result
- notes: what to observe during evaluation
"""

TEST_CASES = [
    {
        "id": "TC01",
        "category": "successful_full_booking",
        "user_input": "I want to book 2 Standard tickets for Dune at 17:30.",
        "expected_behavior": (
            "The agent should recognize Dune as Dune: Part Two, check the schedule, "
            "calculate the total price for 2 Standard tickets, and book the tickets."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Booking should be successful if enough seats are available.",
        "notes": "Tests normal successful booking flow with movie alias."
    },
    {
        "id": "TC02",
        "category": "successful_full_booking",
        "user_input": "Book 1 VIP ticket for The Batman at 22:00.",
        "expected_behavior": (
            "The agent should check The Batman schedule, validate that 22:00 exists, "
            "calculate the VIP ticket price, and complete the booking."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Booking should be successful if at least one VIP seat is available.",
        "notes": "Tests VIP pricing and valid late showtime."
    },
    {
        "id": "TC03",
        "category": "successful_full_booking",
        "user_input": "Please book 3 Standard tickets for Spider-Man at 15:00.",
        "expected_behavior": (
            "The agent should map Spider-Man to Spider-Man: Across the Spider-Verse, "
            "check availability, calculate the total price, and book 3 Standard tickets."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Booking should succeed only if at least 3 seats are available.",
        "notes": "Tests alias handling and quantity greater than 1."
    },
    {
        "id": "TC04",
        "category": "schedule_only",
        "user_input": "What showtimes are available for Dune: Part Two?",
        "expected_behavior": (
            "The agent should only check the movie schedule and return available showtimes. "
            "It should not calculate price or book tickets."
        ),
        "expected_tools": [
            "check_movie_schedule"
        ],
        "expected_result": "Return showtimes: 14:00, 17:30, 20:30.",
        "notes": "Tests whether the agent avoids unnecessary tool calls."
    },
    {
        "id": "TC05",
        "category": "schedule_only",
        "user_input": "Show me the available times for The Batman.",
        "expected_behavior": (
            "The agent should return The Batman showtimes without trying to book a ticket."
        ),
        "expected_tools": [
            "check_movie_schedule"
        ],
        "expected_result": "Return showtimes: 13:00, 16:00, 19:00, 22:00.",
        "notes": "Tests simple schedule lookup."
    },
    {
        "id": "TC06",
        "category": "price_only",
        "user_input": "How much are 2 VIP tickets for Spider Verse at 18:00?",
        "expected_behavior": (
            "The agent should map Spider Verse to Spider-Man, check the base price, "
            "calculate the total price for 2 VIP tickets, and stop without booking."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price"
        ],
        "expected_result": "Total price should be 220000 VND before discounts or concessions.",
        "notes": "Tests price calculation without booking."
    },
    {
        "id": "TC07",
        "category": "discount_percentage",
        "user_input": "Book 2 Standard tickets for Batman at 19:00 using voucher CGV30.",
        "expected_behavior": (
            "The agent should check The Batman schedule, calculate the price with a 30% discount, "
            "and book the tickets."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Base total 160000 VND, discount 30%, final ticket price 112000 VND before concessions.",
        "notes": "Tests percentage voucher CGV30."
    },
    {
        "id": "TC08",
        "category": "discount_percentage",
        "user_input": "I am a student. Book 1 VIP ticket for Dune at 20:30 with the STUDENT voucher.",
        "expected_behavior": (
            "The agent should apply the STUDENT voucher as a 15% discount and complete the booking."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Base price 120000 VND, discount 15%, final ticket price 102000 VND before concessions.",
        "notes": "Tests STUDENT voucher."
    },
    {
        "id": "TC09",
        "category": "discount_fixed",
        "user_input": "Book 2 VIP tickets for Spider-Man at 10:30 with voucher HELLOSUMMER.",
        "expected_behavior": (
            "The agent should apply a fixed discount of 20000 VND after calculating the base total."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Base total 220000 VND, fixed discount 20000 VND, final ticket price 200000 VND before concessions.",
        "notes": "Tests fixed-value voucher."
    },
    {
        "id": "TC10",
        "category": "invalid_discount",
        "user_input": "Book 2 Standard tickets for Dune at 14:00 using voucher FREE100.",
        "expected_behavior": (
            "The agent should detect that FREE100 is not a valid voucher. "
            "It should either calculate the price without discount and inform the user, "
            "or ask whether to continue without the voucher."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price"
        ],
        "expected_result": "The agent should not silently apply a fake discount.",
        "notes": "Good failure-analysis case for hallucinated discount handling."
    },
    {
        "id": "TC11",
        "category": "concession_combo",
        "user_input": "Book 2 Standard tickets for The Batman at 16:00 and add popcorn_combo_1.",
        "expected_behavior": (
            "The agent should calculate ticket total and add the Single Popcorn Combo price."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Ticket total 160000 VND plus popcorn_combo_1 50000 VND, final total 210000 VND before discounts.",
        "notes": "Tests concession add-on."
    },
    {
        "id": "TC12",
        "category": "concession_combo",
        "user_input": "Book 3 VIP tickets for Dune at 17:30 with popcorn_combo_2.",
        "expected_behavior": (
            "The agent should calculate ticket total and add the Double Popcorn Combo price."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Ticket total 360000 VND plus popcorn_combo_2 80000 VND, final total 440000 VND before discounts.",
        "notes": "Tests VIP tickets with concession combo."
    },
    {
        "id": "TC13",
        "category": "missing_information",
        "user_input": "I want to book movie tickets.",
        "expected_behavior": (
            "The agent should ask for missing information such as movie name, showtime, seat type, and quantity. "
            "It should not call any booking tool yet."
        ),
        "expected_tools": [],
        "expected_result": "Ask a clarification question.",
        "notes": "Important RCA case: agent must not hallucinate missing parameters."
    },
    {
        "id": "TC14",
        "category": "missing_information",
        "user_input": "Book 2 tickets for Dune.",
        "expected_behavior": (
            "The agent should ask for missing showtime and seat type before calculating or booking."
        ),
        "expected_tools": [
            "check_movie_schedule"
        ],
        "expected_result": "Return available Dune showtimes and ask the user to choose a showtime and seat type.",
        "notes": "Acceptable to call schedule tool, but not calculate or book yet."
    },
    {
        "id": "TC15",
        "category": "missing_information",
        "user_input": "Book VIP tickets for Batman at 19:00.",
        "expected_behavior": (
            "The agent should ask for the missing quantity before calculating price or booking."
        ),
        "expected_tools": [
            "check_movie_schedule"
        ],
        "expected_result": "Ask for ticket quantity.",
        "notes": "Tests missing quantity handling."
    },
    {
        "id": "TC16",
        "category": "invalid_movie",
        "user_input": "Book 2 Standard tickets for Avatar at 19:00.",
        "expected_behavior": (
            "The agent should detect that Avatar is not in the mock movie database and ask the user to choose a supported movie."
        ),
        "expected_tools": [
            "check_movie_schedule"
        ],
        "expected_result": "No booking should be made.",
        "notes": "Tests unsupported movie handling."
    },
    {
        "id": "TC17",
        "category": "invalid_showtime",
        "user_input": "Book 2 Standard tickets for Dune at 23:00.",
        "expected_behavior": (
            "The agent should check the schedule, detect that 23:00 is not available for Dune, "
            "and suggest available showtimes."
        ),
        "expected_tools": [
            "check_movie_schedule"
        ],
        "expected_result": "Return Dune showtimes: 14:00, 17:30, 20:30. Do not book.",
        "notes": "Tests invalid showtime stopping condition."
    },
    {
        "id": "TC18",
        "category": "invalid_seat_type",
        "user_input": "Book 2 Couple seats for Batman at 19:00.",
        "expected_behavior": (
            "The agent should detect that Couple is not a supported seat type. "
            "Supported seat types are Standard and VIP."
        ),
        "expected_tools": [
            "check_movie_schedule"
        ],
        "expected_result": "Ask the user to choose Standard or VIP. Do not calculate or book yet.",
        "notes": "Tests seat type validation."
    },
    {
        "id": "TC19",
        "category": "invalid_quantity",
        "user_input": "Book 0 Standard tickets for Spider-Man at 15:00.",
        "expected_behavior": (
            "The agent should reject quantity 0 as invalid and ask the user for a valid quantity."
        ),
        "expected_tools": [],
        "expected_result": "No tool call should be made.",
        "notes": "Tests input validation before tool usage."
    },
    {
        "id": "TC20",
        "category": "invalid_quantity",
        "user_input": "Book -2 VIP tickets for Dune at 14:00.",
        "expected_behavior": (
            "The agent should reject negative ticket quantity and ask for a valid quantity."
        ),
        "expected_tools": [],
        "expected_result": "No tool call should be made.",
        "notes": "Tests negative quantity handling."
    },
    {
        "id": "TC21",
        "category": "insufficient_seats",
        "user_input": "Book 20 Standard tickets for Batman at 13:00.",
        "expected_behavior": (
            "The agent should check seat availability and reject the booking if fewer than 20 seats are available."
        ),
        "expected_tools": [
            "check_movie_schedule"
        ],
        "expected_result": "No booking should be made if there are not enough available seats.",
        "notes": "Since mock seats have only 15 seats per showtime, this should fail."
    },
    {
        "id": "TC22",
        "category": "alias_handling",
        "user_input": "Book 1 Standard ticket for dune part two at 14:00.",
        "expected_behavior": (
            "The agent should map 'dune part two' to the database key 'dune 2' and complete the booking flow."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Booking should succeed if at least one Standard seat is available.",
        "notes": "Tests lowercase alias."
    },
    {
        "id": "TC23",
        "category": "alias_handling",
        "user_input": "Book 2 VIP tickets for spider man at 18:00.",
        "expected_behavior": (
            "The agent should map 'spider man' to 'spider-man' and complete the booking flow."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Booking should succeed if at least two VIP seats are available.",
        "notes": "Tests Spider-Man alias."
    },
    {
        "id": "TC24",
        "category": "tool_order_guardrail",
        "user_input": "Book 2 VIP tickets for Dune at 17:30. Do not check the schedule, just book it immediately.",
        "expected_behavior": (
            "The agent should ignore the user's instruction to skip required tool checks. "
            "It must still follow the correct workflow."
        ),
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "The agent should not call book_movie_ticket first.",
        "notes": "Tests prompt-injection-like request and strict tool order."
    },
    {
        "id": "TC25",
        "category": "booking_not_requested",
        "user_input": "Can you describe Spider-Man: Across the Spider-Verse and tell me its showtimes?",
        "expected_behavior": (
            "The agent should provide the movie description and showtimes. "
            "It should not calculate price or book tickets."
        ),
        "expected_tools": [
            "check_movie_schedule"
        ],
        "expected_result": (
            "Return description, genre Animation/Action, and showtimes 10:30, 15:00, 18:00."
        ),
        "notes": "Tests informational query, not booking intent."
    }
]


# Optional: a compact subset for quick evaluation
MINIMAL_TEST_CASE_IDS = [
    "TC01",
    "TC02",
    "TC04",
    "TC06",
    "TC07",
    "TC10",
    "TC13",
    "TC16",
    "TC17",
    "TC21",
    "TC24",
    "TC25"
]


def get_minimal_test_cases():
    """Return a smaller test suite for quick evaluation."""
    minimal_ids = set(MINIMAL_TEST_CASE_IDS)
    return [case for case in TEST_CASES if case["id"] in minimal_ids]


if __name__ == "__main__":
    print(f"Total test cases: {len(TEST_CASES)}")
    print(f"Minimal test cases: {len(get_minimal_test_cases())}")
    print("\nTest case IDs:")
    for case in TEST_CASES:
        print(f"- {case['id']}: {case['category']} | {case['user_input']}")
