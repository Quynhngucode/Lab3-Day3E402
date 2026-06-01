The architecture for the cinema ticket booking system consists of three distinct tools designed to handle the sequence of checking availability, processing costs, and confirming the reservation.

### check_movie_schedule

**Description:** Retrieves available showtimes and base ticket prices for a specific movie at a designated cinema on a given date.
**Parameters:**

* movie_name (string): The title of the movie.
* cinema_name (string): The name of the cinema branch.
* date (string): The intended date for the screening.
**Returns:** A list of available showtimes and the standard base price per ticket.

### calculate_total_price

**Description:** Computes the final ticket cost based on the base price, quantity, seat type multiplier, and applicable promotional discounts.
**Parameters:**

* base_price (number): The standard price of a single ticket retrieved from the schedule.
* quantity (integer): The number of tickets to purchase.
* seat_type (string): The category of the seat, such as standard or VIP.
* discount_code (string): An optional promotional code for price reduction.
**Returns:** The total monetary value required for the transaction.

### book_movie_ticket

**Description:** Executes the final reservation process and generates a booking confirmation upon verifying the details.
**Parameters:**

* movie_name (string): The title of the movie.
* cinema_name (string): The name of the cinema branch.
* showtime (string): The selected time for the screening.
* seat_type (string): The chosen category of the seat.
* quantity (integer): The number of seats reserved.
* total_price (number): The finalized payment amount calculated in the previous step.
**Returns:** A unique booking confirmation code and the status of the reservation.