import os
import json
from typing import List, Dict, Any, Optional

class ShortTermMemory:
    """
    In-memory storage for the current conversation session.
    """
    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        self.messages: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_messages * 2:
            # Keep only the last max_messages exchanges
            self.messages = self.messages[-(self.max_messages * 2):]

    def get_history(self) -> List[Dict[str, str]]:
        return self.messages

    def get_history_as_string(self) -> str:
        history_str = ""
        for msg in self.messages:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_str += f"{role_label}: {msg['content']}\n"
        return history_str

    def clear(self):
        self.messages = []


class LongTermMemory:
    """
    JSON file-backed persistent memory to track user preferences, past bookings, and loyalty status.
    """
    def __init__(self, file_path: str = "memory/user_profile.json"):
        # Resolve to absolute path relative to this file's project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.file_path = os.path.join(project_root, file_path)
        # Ensure directory exists
        dir_name = os.path.dirname(self.file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self.data: Dict[str, Any] = self._load_default_profile()
        self.load()

    def _load_default_profile(self) -> Dict[str, Any]:
        return {
            "user_name": "Khách hàng",
            "favorite_genres": ["Sci-Fi", "Action"],
            "preferred_seat_type": "VIP",
            "saved_vouchers": ["CGV30", "STUDENT"],
            "past_bookings": []
        }

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                # Fallback to default on corrupt file
                self.data = self._load_default_profile()
        else:
            self.save()

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving long-term memory: {e}")

    def update_profile(self, key: str, value: Any):
        self.data[key] = value
        self.save()

    def get_profile(self) -> Dict[str, Any]:
        return self.data

    def get_profile_as_string(self) -> str:
        # Format user traits neatly for the agent system prompt
        profile = self.data
        bookings_summary = []
        for bk in profile.get("past_bookings", []):
            bookings_summary.append(f"Booking {bk.get('booking_id')} for movie '{bk.get('movie')}' at {bk.get('showtime')} (seats: {', '.join(bk.get('seats', []))})")
            
        summary = f"""User Name: {profile.get('user_name', 'Khách hàng')}
Favorite Genres: {', '.join(profile.get('favorite_genres', []))}
Preferred Seat Class: {profile.get('preferred_seat_type', 'VIP')}
Available Vouchers in Wallet: {', '.join(profile.get('saved_vouchers', []))}
Past Bookings History:
"""
        if bookings_summary:
            summary += "\n".join([f"- {b}" for b in bookings_summary])
        else:
            summary += "- No bookings yet."
        return summary
