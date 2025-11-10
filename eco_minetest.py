# -*- coding: utf-8 -*-
import re
import time
import json
from datetime import datetime
from collections import defaultdict

class MinetestMonitor:
    def __init__(self, log_file_path, stats_file='minetest_stats.json'):
        self.log_file_path = log_file_path
        self.stats_file = stats_file
        self.stats = self.load_stats()
    
    def load_stats(self):
        """Load existing stats from file or create new."""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_stats(self):
        """Save current stats to file."""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def init_player(self, player):
        """Initialize a new player's stats."""
        if player not in self.stats:
            self.stats[player] = {
                'stone_dug': 0,
                'sand_dug': 0,
                'farming_placed': 0,
                'last_seen': None
            }
    
    def parse_and_update(self, line, verbose=True):
        """Parse log line and update stats if relevant."""
        # Pattern for digging actions
        dig_pattern = r'ACTION\[Server\]: (\w+) digs ([\w:]+) at'
        dig_match = re.search(dig_pattern, line)
        
        if dig_match:
            player = dig_match.group(1)
            block = dig_match.group(2)
            
            self.init_player(player)
            
            # Check if it's stone (default:stone, default:stone_with_coal, etc.)
            if block.startswith('default:stone'):
                self.stats[player]['stone_dug'] += 1
                if verbose:
                    print(f"[+] {player} dug stone! Total: {self.stats[player]['stone_dug']}")
                return True
            
            # Check if it's sand
            elif block == 'default:sand':
                self.stats[player]['sand_dug'] += 1
                if verbose:
                    print(f"[+] {player} dug sand! Total: {self.stats[player]['sand_dug']}")
                return True
        
        # Pattern for placing actions
        place_pattern = r'ACTION\[Server\]: (\w+) places node ([\w:]+) at'
        place_match = re.search(place_pattern, line)
        
        if place_match:
            player = place_match.group(1)
            block = place_match.group(2)
            
            self.init_player(player)
            
            # Check if it's a farming item
            if block.startswith('farming:'):
                self.stats[player]['farming_placed'] += 1
                if verbose:
                    print(f"[+] {player} placed {block}! Total farming: {self.stats[player]['farming_placed']}")
                return True
        
        return False
    
    def process_existing_log(self, clear_stats=False):
        """Process entire existing log file (for testing/catching up)."""
        if clear_stats:
            self.stats = {}
            print("Cleared existing stats.")
        
        print(f"Processing existing log: {self.log_file_path}")
        print("This may take a moment...")
        print("-" * 50)
        
        line_count = 0
        event_count = 0
        
        try:
            with open(self.log_file_path, 'r') as log_file:
                for line in log_file:
                    line_count += 1
                    if self.parse_and_update(line.strip(), verbose=False):
                        event_count += 1
                    
                    # Progress indicator every 1000 lines
                    if line_count % 1000 == 0:
                        print(f"Processed {line_count} lines, found {event_count} events...")
        
            print(f"\n[+] Processing complete!")
            print(f"  Total lines processed: {line_count}")
            print(f"  Relevant events found: {event_count}")
            
            self.save_stats()
            print(f"  Stats saved to: {self.stats_file}")
            
        except FileNotFoundError:
            print(f"Error: Log file not found at {self.log_file_path}")
        except Exception as e:
            print(f"Error processing log: {e}")
    
    def print_table(self):
        """Print statistics in a pretty formatted table."""
        if not self.stats:
            print("\nNo statistics available yet.\n")
            return
        
        # Sort by total activity
        sorted_players = sorted(
            self.stats.items(),
            key=lambda x: x[1]['stone_dug'] + x[1]['sand_dug'] + x[1]['farming_placed'],
            reverse=True
        )
        
        # Calculate column widths
        max_name_len = max(len(player) for player in self.stats.keys())
        max_name_len = max(max_name_len, len("Player"))
        
        # Header
        print("\n" + "=" * (max_name_len + 52))
        print(f"{'Player':<{max_name_len}} | {'Stone Dug':>10} | {'Sand Dug':>10} | {'Farming':>10} | {'Total':>10}")
        print("=" * (max_name_len + 52))
        
        # Data rows
        grand_totals = {'stone': 0, 'sand': 0, 'farming': 0}
        
        for player, stats in sorted_players:
            stone = stats['stone_dug']
            sand = stats['sand_dug']
            farming = stats['farming_placed']
            total = stone + sand + farming
            
            grand_totals['stone'] += stone
            grand_totals['sand'] += sand
            grand_totals['farming'] += farming
            
            print(f"{player:<{max_name_len}} | {stone:>10,} | {sand:>10,} | {farming:>10,} | {total:>10,}")
        
        # Footer with totals
        print("-" * (max_name_len + 52))
        grand_total = grand_totals['stone'] + grand_totals['sand'] + grand_totals['farming']
        print(f"{'TOTAL':<{max_name_len}} | {grand_totals['stone']:>10,} | {grand_totals['sand']:>10,} | {grand_totals['farming']:>10,} | {grand_total:>10,}")
        print("=" * (max_name_len + 52))
        
        # Additional stats
        print(f"\nTotal players: {len(self.stats)}")
        print(f"Total events tracked: {grand_total:,}")
        print()
    
    def monitor(self):
        """Monitor the log file in real-time."""
        print(f"Starting Minetest monitor...")
        print(f"Tracking: stone/sand dug, farming placed")
        print(f"Stats saved to: {self.stats_file}")
        print("-" * 50)
        
        with open(self.log_file_path, 'r') as log_file:
            # Start from end of file (only monitor new entries)
            log_file.seek(0, 2)
            
            save_counter = 0
            
            while True:
                line = log_file.readline()
                
                if not line:
                    time.sleep(0.1)  # Wait for new data
                    continue
                
                # Parse and update stats
                if self.parse_and_update(line.strip()):
                    save_counter += 1
                    
                    # Save stats every 10 events to avoid excessive disk writes
                    if save_counter >= 10:
                        self.save_stats()
                        save_counter = 0
    
    def print_summary(self):
        """Print current statistics summary (legacy method, use print_table instead)."""
        self.print_table()

# Usage examples
if __name__ == "__main__":
    # Replace with your actual log file path
    LOG_FILE = "/path/to/minetest/debug.txt"
    
    monitor = MinetestMonitor(LOG_FILE)
    
    # Example 1: Process existing log file (for testing)
    print("Choose mode:")
    print("1. Process existing log file (test mode)")
    print("2. Monitor log file in real-time")
    print("3. Just show current stats table")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        # Test mode - process entire existing log
        clear = input("Clear existing stats? (y/n): ").strip().lower()
        monitor.process_existing_log(clear_stats=(clear == 'y'))
        monitor.print_table()
        
    elif choice == "2":
        # Real-time monitoring mode
        try:
            monitor.monitor()
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
            monitor.save_stats()
            monitor.print_table()
            print(f"\nStats saved to {monitor.stats_file}")
    
    elif choice == "3":
        # Just display stats
        monitor.print_table()
    
    else:
        print("Invalid choice. Exiting.")
