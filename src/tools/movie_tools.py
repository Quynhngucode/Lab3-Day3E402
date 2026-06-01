import os
import random
import json
from typing import List, Dict, Any, Optional

# Mock database
MOCK_MOVIES = {
    "dune 2": {
        "title": "Dune: Part Two",
        "genre": "Sci-Fi/Adventure",
        "description": "Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.",
        "showtimes": ["14:00", "17:30", "20:30"],
        "prices": {"Standard": 80000, "VIP": 120000}
    },
    "batman": {
        "title": "The Batman",
        "genre": "Action/Crime",
        "description": "Batman ventures into Gotham City's underworld when a sadistic killer leaves behind a trail of cryptic clues.",
        "showtimes": ["13:00", "16:00", "19:00", "22:00"],
        "prices": {"Standard": 80000, "VIP": 120000}
    },
    "spider-man": {
        "title": "Spider-Man: Across the Spider-Verse",
        "genre": "Animation/Action",
        "description": "Miles Morales catapults across the Multiverse, where he encounters a team of Spider-People charged with protecting its very existence.",
        "showtimes": ["10:30", "15:00", "18:00"],
        "prices": {"Standard": 70000, "VIP": 110000}
    }
}

# Seating configuration: A1-A5 (VIP), B1-B5 (Standard), C1-C5 (Standard)
MOCK_SEATS = {}
for movie in MOCK_MOVIES:
    for time in MOCK_MOVIES[movie]["showtimes"]:
        key = f"{movie}_{time}"
        # Randomly book some seats to make it realistic
        seats = {}
        for row in ["A", "B", "C"]:
            for col in range(1, 6):
                seat_id = f"{row}{col}"
                # 30% chance seat is already booked
                seats[seat_id] = "Booked" if random.random() < 0.3 else "Available"
        MOCK_SEATS[key] = seats

MOVIE_ALIASES = {
    "dune: part two": "dune 2",
    "dune part two": "dune 2",
    "dune": "dune 2",
    "the batman": "batman",
    "spider-man across the spider-verse": "spider-man",
    "spider man": "spider-man",
    "spider verse": "spider-man"
}


def _fuzzy_match_movie(movie_name: str) -> str:
    """Returns the internal movie key matching the given name, or empty string."""
    m_lower = movie_name.lower().strip()
    
    # 1. Direct alias lookup
    if m_lower in MOVIE_ALIASES:
        return MOVIE_ALIASES[m_lower]
    
    # 2. Direct key match
    if m_lower in MOCK_MOVIES:
        return m_lower
    
    # 3. Substring match (both directions)
    for key in MOCK_MOVIES:
        if key in m_lower or m_lower in key:
            return key
    
    # 4. Word overlap: check if any key word appears in input
    for key in MOCK_MOVIES:
        key_words = set(key.split())
        input_words = set(m_lower.replace(':', '').replace('-', ' ').split())
        # Need at least one meaningful word match (length > 2)
        overlap = [w for w in key_words & input_words if len(w) > 2]
        if overlap:
            return key

    return ""


MOCK_VOUCHERS = {
    "CGV30": {"type": "percentage", "value": 0.30},
    "STUDENT": {"type": "percentage", "value": 0.15},
    "HELLOSUMMER": {"type": "fixed", "value": 20000}
}

MOCK_CONCESSIONS = {
    "popcorn_combo_1": {"name": "Single Popcorn Combo (1 Popcorn + 1 Soft Drink)", "price": 50000},
    "popcorn_combo_2": {"name": "Double Popcorn Combo (1 Big Popcorn + 2 Soft Drinks)", "price": 80000}
}


def get_movie_info(movie_name: str) -> str:
    """
    Get showtimes, genre, standard and VIP ticket prices, and short description of a movie.
    Args:
        movie_name: The name of the movie (e.g. 'dune 2', 'batman', 'spider-man').
    """
    found_key = _fuzzy_match_movie(movie_name)

    if not found_key:
        return json.dumps({
            "status": "error",
            "message": f"Movie '{movie_name}' not found. Available movies: {', '.join([m['title'] for m in MOCK_MOVIES.values()])}"
        }, ensure_ascii=False)

    movie_data = MOCK_MOVIES[found_key]
    return json.dumps({
        "status": "success",
        "movie_key": found_key,
        "title": movie_data["title"],
        "genre": movie_data["genre"],
        "description": movie_data["description"],
        "showtimes": movie_data["showtimes"],
        "prices": movie_data["prices"]
    }, ensure_ascii=False)


def check_seat_availability(movie_name: str, showtime: str) -> str:
    """
    Check which seats are available for a given movie and showtime.
    Seats starting with 'A' are VIP, others (B and C) are Standard.
    Args:
        movie_name: The name of the movie (e.g., 'dune 2', 'batman').
        showtime: The showtime (e.g., '19:00', '20:30').
    """
    found_key = _fuzzy_match_movie(movie_name)

    if not found_key:
        return json.dumps({"status": "error", "message": f"Movie '{movie_name}' not found."}, ensure_ascii=False)

    time_key = f"{found_key}_{showtime.strip()}"
    if time_key not in MOCK_SEATS:
        # Try to find matching showtime
        movie_showtimes = MOCK_MOVIES[found_key]["showtimes"]
        return json.dumps({
            "status": "error", 
            "message": f"Showtime '{showtime}' not found for '{movie_name}'. Available: {', '.join(movie_showtimes)}"
        }, ensure_ascii=False)

    seats = MOCK_SEATS[time_key]
    available_seats = [seat for seat, status in seats.items() if status == "Available"]
    booked_seats = [seat for seat, status in seats.items() if status == "Booked"]

    return json.dumps({
        "status": "success",
        "movie": MOCK_MOVIES[found_key]["title"],
        "showtime": showtime,
        "available_seats": sorted(available_seats),
        "booked_seats": sorted(booked_seats)
    }, ensure_ascii=False)


def apply_voucher(voucher_code: str) -> str:
    """
    Check if a voucher/coupon code is valid and return the discount details.
    Args:
        voucher_code: The code to check (e.g. 'CGV30', 'STUDENT').
    """
    code = voucher_code.upper().strip()
    if code in MOCK_VOUCHERS:
        voucher = MOCK_VOUCHERS[code]
        return json.dumps({
            "status": "success",
            "voucher": code,
            "type": voucher["type"],
            "value": voucher["value"]
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "error",
            "message": f"Voucher code '{voucher_code}' is invalid or expired."
        }, ensure_ascii=False)


def calculate_total_price(ticket_type: str, quantity: int, popcorn_combo_type: int = 0, voucher_code: str = "") -> str:
    """
    Calculate the total cost before placing a booking.
    Args:
        ticket_type: 'Standard' or 'VIP' (VIP tickets are standard price + VIP premium).
        quantity: Number of tickets.
        popcorn_combo_type: 0 for none, 1 for Single Combo (50,000 VND), 2 for Double Combo (80,000 VND).
        voucher_code: Optional voucher code (e.g. 'CGV30', 'STUDENT').
    """
    # Standard pricing base: 80,000 for Standard, 120,000 for VIP (using Dune 2 prices as base standard if not specified)
    base_price = 80000 if ticket_type.lower() == "standard" else 120000
    ticket_total = base_price * quantity
    
    concessions_total = 0
    concessions_name = "None"
    if popcorn_combo_type == 1:
        concessions_total = MOCK_CONCESSIONS["popcorn_combo_1"]["price"]
        concessions_name = MOCK_CONCESSIONS["popcorn_combo_1"]["name"]
    elif popcorn_combo_type == 2:
        concessions_total = MOCK_CONCESSIONS["popcorn_combo_2"]["price"]
        concessions_name = MOCK_CONCESSIONS["popcorn_combo_2"]["name"]

    subtotal = ticket_total + concessions_total
    discount_amount = 0
    discount_msg = "No voucher applied"

    if voucher_code:
        v_res = json.loads(apply_voucher(voucher_code))
        if v_res["status"] == "success":
            v_type = v_res["type"]
            v_val = v_res["value"]
            if v_type == "percentage":
                discount_amount = int(subtotal * v_val)
                discount_msg = f"{v_res['voucher']} ({int(v_val * 100)}% off)"
            elif v_type == "fixed":
                discount_amount = min(subtotal, v_val)
                discount_msg = f"{v_res['voucher']} (-{v_val} VND)"
        else:
            discount_msg = f"Invalid voucher: {v_res['message']}"

    total = subtotal - discount_amount

    return json.dumps({
        "status": "success",
        "ticket_type": ticket_type,
        "ticket_price": base_price,
        "quantity": quantity,
        "ticket_total": ticket_total,
        "concessions_combo": concessions_name,
        "concessions_total": concessions_total,
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "discount_info": discount_msg,
        "total_price": total
    }, ensure_ascii=False)


def book_ticket(movie_name: str, showtime: str, seats: List[str], ticket_type: str, popcorn_combo_type: int = 0, voucher_code: str = "") -> str:
    """
    Book tickets by reserving specific seats, calculating total price, and generating a Booking ID.
    Args:
        movie_name: Name of the movie (e.g. 'dune 2', 'batman').
        showtime: Show time (e.g. '19:00', '20:30').
        seats: List of seat IDs to book (e.g. ['A1', 'A2']).
        ticket_type: 'Standard' or 'VIP' (must match the seats: A rows are VIP, B/C rows are Standard).
        popcorn_combo_type: 0 for none, 1 for Single Combo, 2 for Double Combo.
        voucher_code: Optional voucher code.
    """
    found_key = _fuzzy_match_movie(movie_name)

    if not found_key:
        return json.dumps({"status": "error", "message": f"Movie '{movie_name}' not found."}, ensure_ascii=False)

    time_key = f"{found_key}_{showtime.strip()}"
    if time_key not in MOCK_SEATS:
        return json.dumps({"status": "error", "message": f"Showtime '{showtime}' not found for this movie."}, ensure_ascii=False)

    db_seats = MOCK_SEATS[time_key]
    
    # Check if seats are available
    unavailable = []
    for seat in seats:
        seat_cleaned = seat.strip().upper()
        if seat_cleaned not in db_seats:
            return json.dumps({"status": "error", "message": f"Seat '{seat}' does not exist. Available seats are A1-A5, B1-B5, C1-C5."}, ensure_ascii=False)
        if db_seats[seat_cleaned] == "Booked":
            unavailable.append(seat)

    if unavailable:
        return json.dumps({
            "status": "error", 
            "message": f"Seats {', '.join(unavailable)} are already booked. Please choose other seats."
        }, ensure_ascii=False)

    # Validate seat row vs ticket type
    for seat in seats:
        seat_cleaned = seat.strip().upper()
        row = seat_cleaned[0]
        if row == "A" and ticket_type.upper() != "VIP":
            return json.dumps({"status": "error", "message": f"Seat '{seat_cleaned}' is a VIP seat, but ticket_type is '{ticket_type}'."}, ensure_ascii=False)
        if row != "A" and ticket_type.upper() == "VIP":
            return json.dumps({"status": "error", "message": f"Seat '{seat_cleaned}' is a Standard seat, but ticket_type is '{ticket_type}'."}, ensure_ascii=False)

    # Book the seats
    for seat in seats:
        seat_cleaned = seat.strip().upper()
        db_seats[seat_cleaned] = "Booked"

    # Calculate total
    calc_res_str = calculate_total_price(ticket_type, len(seats), popcorn_combo_type, voucher_code)
    calc_res = json.loads(calc_res_str)

    booking_id = f"BK-{random.randint(100000, 999999)}"

    return json.dumps({
        "status": "success",
        "booking_id": booking_id,
        "movie": MOCK_MOVIES[found_key]["title"],
        "showtime": showtime,
        "seats": seats,
        "ticket_type": ticket_type,
        "popcorn_combo": calc_res["concessions_combo"],
        "subtotal": calc_res["subtotal"],
        "discount_amount": calc_res["discount_amount"],
        "total_price": calc_res["total_price"],
        "message": f"Booking successful! Your booking ID is {booking_id}."
    }, ensure_ascii=False)


def web_search(query: str) -> str:
    """
    Search the web (via Tavily if API key is available, or fallback to mock data) for queries about movies, schedules, or reviews.
    Args:
        query: Search query string.
    """
    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    if tavily_api_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_api_key)
            result = client.search(query=query)
            return json.dumps({"status": "success", "results": result.get("results", [])}, ensure_ascii=False)
        except Exception as e:
            # Fallback if Tavily import or call fails
            pass

    # Mock Search DB
    q_lower = query.lower()
    mock_search_results = []
    
    if "dune" in q_lower:
        mock_search_results.append({
            "title": "Dune: Part Two Review - Rotten Tomatoes",
            "url": "https://www.rottentomatoes.com/m/dune_part_two",
            "content": "Dune: Part Two has a 95% Tomatometer score. Critics praise Denis Villeneuve's masterpiece for its stunning visuals, grand scale, and powerful performances by Timothée Chalamet and Zendaya."
        })
    elif "batman" in q_lower:
        mock_search_results.append({
            "title": "The Batman Review - IMDb",
            "url": "https://www.imdb.com/title/tt1877830/",
            "content": "The Batman (2022) is rated 7.8/10. It is a gritty, noir-style detective thriller starring Robert Pattinson as a dark, brooding, and realistic version of Gotham's Caped Crusader."
        })
    elif "spider-man" in q_lower or "spider-verse" in q_lower:
        mock_search_results.append({
            "title": "Spider-Man: Across the Spider-Verse Review",
            "url": "https://www.ign.com/articles/spider-man-across-the-spider-verse-review",
            "content": "Across the Spider-Verse is a stunning achievement in animation, scoring 10/10 on IGN. It expands on Miles Morales' story with emotional depth, humor, and spectacular multi-dimensional art style."
        })
    else:
        mock_search_results.append({
            "title": "Upcoming Movies 2026 - Cinema Schedules",
            "url": "https://example.com/movies2026",
            "content": f"Searching schedule for '{query}'. Current playing blockbusters are Dune: Part Two, The Batman, and Spider-Man: Across the Spider-Verse. VIP ticket price base is 120k VND, Standard is 80k VND."
        })

    return json.dumps({
        "status": "success",
        "query": query,
        "results": mock_search_results
    }, ensure_ascii=False)
