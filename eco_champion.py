# -*- coding: utf-8 -*-
import re
import time
import json
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
        except (FileNotFoundError, IOError):
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
                'dirt_dug': 0,
                'coal_dug': 0,
                'copper_dug': 0,
                'tin_dug': 0,
                'iron_dug': 0,
                'gold_dug': 0,
                'diamond_dug': 0,
                'farming_placed': 0,
                'last_seen': None
            }
    
    def calculate_eco_score(self, player_stats):
        """
        Calculate environmental responsibility score.
        
        Scoring system:
        - Farming activities: +10 points each (renewable, adds to world)
        - Valuable ore mining: +2 points each (purposeful mining)
        - Regular resource extraction: -1 point each (depletes environment)
        - Dirt/sand removal: -2 points each (landscape destruction)
        
        Higher score = more environmentally responsible
        """
        # Positive actions (adding to the world)
        farming_score = player_stats['farming_placed'] * 10
        
        # Neutral to slightly positive (purposeful mining for resources)
        ore_score = (
            player_stats['coal_dug'] * 2 +
            player_stats['copper_dug'] * 2 +
            player_stats['tin_dug'] * 2 +
            player_stats['iron_dug'] * 2 +
            player_stats['gold_dug'] * 2 +
            player_stats['diamond_dug'] * 2
        )
        
        # Negative actions (removing basic resources)
        extraction_penalty = (
            player_stats['stone_dug'] * -1
        )
        
        # Heavy penalty for landscape destruction
        landscape_penalty = (
            player_stats['dirt_dug'] * -2 +
            player_stats['sand_dug'] * -2
        )
        
        total_score = farming_score + ore_score + extraction_penalty + landscape_penalty
        
        return {
            'total_score': total_score,
            'farming_score': farming_score,
            'ore_score': ore_score,
            'extraction_penalty': extraction_penalty,
            'landscape_penalty': landscape_penalty
        }
    
    def get_eco_rating(self, score):
        """Get a text rating based on eco score."""
        if score >= 500:
            return "ECO CHAMPION"
        elif score >= 200:
            return "Environmentalist"
        elif score >= 50:
            return "Eco-Friendly"
        elif score >= 0:
            return "Balanced"
        elif score >= -100:
            return "Resource User"
        elif score >= -300:
            return "Strip Miner"
        else:
            return "LANDSCAPE DESTROYER"
    
    def parse_and_update(self, line, verbose=True):
        """Parse log line and update stats if relevant."""
        # Pattern for digging actions
        dig_pattern = r'ACTION\[Server\]: (\w+) digs ([\w:]+) at'
        dig_match = re.search(dig_pattern, line)
        
        if dig_match:
            player = dig_match.group(1)
            block = dig_match.group(2)
            
            self.init_player(player)
            
            # Check for specific ore types first (before general stone)
            if block == 'default:stone_with_coal':
                self.stats[player]['coal_dug'] += 1
                if verbose:
                    print("[+] {} dug COAL! Total: {}".format(player, self.stats[player]['coal_dug']))
                return True
            
            elif block == 'default:stone_with_copper':
                self.stats[player]['copper_dug'] += 1
                if verbose:
                    print("[+] {} dug COPPER! Total: {}".format(player, self.stats[player]['copper_dug']))
                return True
            
            elif block == 'default:stone_with_tin':
                self.stats[player]['tin_dug'] += 1
                if verbose:
                    print("[+] {} dug TIN! Total: {}".format(player, self.stats[player]['tin_dug']))
                return True
            
            elif block == 'default:stone_with_iron':
                self.stats[player]['iron_dug'] += 1
                if verbose:
                    print("[+] {} dug IRON! Total: {}".format(player, self.stats[player]['iron_dug']))
                return True
            
            elif block == 'default:stone_with_gold':
                self.stats[player]['gold_dug'] += 1
                if verbose:
                    print("[+] {} dug GOLD! Total: {}".format(player, self.stats[player]['gold_dug']))
                return True
            
            elif block == 'default:stone_with_diamond':
                self.stats[player]['diamond_dug'] += 1
                if verbose:
                    print("[+] {} dug DIAMOND! Total: {}".format(player, self.stats[player]['diamond_dug']))
                return True
            
            # Check for regular stone (only plain stone, not ores)
            elif block == 'default:stone':
                self.stats[player]['stone_dug'] += 1
                if verbose:
                    print("[+] {} dug stone! Total: {}".format(player, self.stats[player]['stone_dug']))
                return True
            
            # Check if it's sand
            elif block == 'default:sand':
                self.stats[player]['sand_dug'] += 1
                if verbose:
                    print("[+] {} dug sand! Total: {}".format(player, self.stats[player]['sand_dug']))
                return True
            
            # Check if it's dirt
            elif block == 'default:dirt' or block == 'default:dirt_with_grass':
                self.stats[player]['dirt_dug'] += 1
                if verbose:
                    print("[+] {} dug dirt! Total: {}".format(player, self.stats[player]['dirt_dug']))
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
                    print("[+] {} placed {}! Total farming: {}".format(player, block, self.stats[player]['farming_placed']))
                return True
        
        return False
    
    def process_existing_log(self, clear_stats=False):
        """Process entire existing log file (for testing/catching up)."""
        if clear_stats:
            self.stats = {}
            print("Cleared existing stats.")
        
        print("Processing existing log: {}".format(self.log_file_path))
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
                        print("Processed {} lines, found {} events...".format(line_count, event_count))
        
            print("\n[+] Processing complete!")
            print("  Total lines processed: {}".format(line_count))
            print("  Relevant events found: {}".format(event_count))
            
            self.save_stats()
            print("  Stats saved to: {}".format(self.stats_file))
            
        except IOError:
            print("Error: Log file not found at {}".format(self.log_file_path))
        except Exception as e:
            print("Error processing log: {}".format(e))
    
    def print_table(self):
        """Print statistics in a pretty formatted table."""
        if not self.stats:
            print("\nNo statistics available yet.\n")
            return
        
        # Sort by total activity
        sorted_players = sorted(
            self.stats.items(),
            key=lambda x: sum([
                x[1]['stone_dug'], x[1]['sand_dug'], x[1]['dirt_dug'],
                x[1]['coal_dug'], x[1]['copper_dug'], x[1]['tin_dug'],
                x[1]['iron_dug'], x[1]['gold_dug'], x[1]['diamond_dug'],
                x[1]['farming_placed']
            ]),
            reverse=True
        )
        
        # Calculate column widths
        max_name_len = max(len(player) for player in self.stats.keys())
        max_name_len = max(max_name_len, len("Player"))
        
        # Header
        separator = "=" * (max_name_len + 125)
        print("\n" + separator)
        header = "{:<{}} | {:>6} | {:>6} | {:>6} | {:>6} | {:>6} | {:>6} | {:>6} | {:>6} | {:>6} | {:>7} | {:>8}".format(
            "Player", max_name_len, "Stone", "Sand", "Dirt", "Coal", "Copper", "Tin", "Iron", "Gold", "Diamnd", "Farming", "Total"
        )
        print(header)
        print(separator)
        
        # Data rows
        grand_totals = {
            'stone': 0, 'sand': 0, 'dirt': 0, 'coal': 0, 
            'copper': 0, 'tin': 0, 'iron': 0, 'gold': 0, 
            'diamond': 0, 'farming': 0
        }
        
        for player, stats in sorted_players:
            stone = stats['stone_dug']
            sand = stats['sand_dug']
            dirt = stats['dirt_dug']
            coal = stats['coal_dug']
            copper = stats['copper_dug']
            tin = stats['tin_dug']
            iron = stats['iron_dug']
            gold = stats['gold_dug']
            diamond = stats['diamond_dug']
            farming = stats['farming_placed']
            total = stone + sand + dirt + coal + copper + tin + iron + gold + diamond + farming
            
            grand_totals['stone'] += stone
            grand_totals['sand'] += sand
            grand_totals['dirt'] += dirt
            grand_totals['coal'] += coal
            grand_totals['copper'] += copper
            grand_totals['tin'] += tin
            grand_totals['iron'] += iron
            grand_totals['gold'] += gold
            grand_totals['diamond'] += diamond
            grand_totals['farming'] += farming
            
            row = "{:<{}} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>7,} | {:>8,}".format(
                player, max_name_len, stone, sand, dirt, coal, copper, tin, iron, gold, diamond, farming, total
            )
            print(row)
        
        # Footer with totals
        print("-" * (max_name_len + 125))
        grand_total = sum(grand_totals.values())
        total_row = "{:<{}} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>6,} | {:>7,} | {:>8,}".format(
            "TOTAL", max_name_len, 
            grand_totals['stone'], grand_totals['sand'], grand_totals['dirt'],
            grand_totals['coal'], grand_totals['copper'], grand_totals['tin'],
            grand_totals['iron'], grand_totals['gold'], grand_totals['diamond'],
            grand_totals['farming'], grand_total
        )
        print(total_row)
        print(separator)
        
        # Additional stats
        print("\nTotal players: {}".format(len(self.stats)))
        print("Total events tracked: {:,}".format(grand_total))
        print()
    
    def print_eco_leaderboard(self):
        """Print environmental responsibility leaderboard."""
        if not self.stats:
            print("\nNo statistics available yet.\n")
            return
        
        # Calculate eco scores for all players
        player_scores = []
        for player, stats in self.stats.items():
            eco_data = self.calculate_eco_score(stats)
            player_scores.append({
                'player': player,
                'score': eco_data['total_score'],
                'rating': self.get_eco_rating(eco_data['total_score']),
                'farming': stats['farming_placed'],
                'ores': (stats['coal_dug'] + stats['copper_dug'] + stats['tin_dug'] + 
                        stats['iron_dug'] + stats['gold_dug'] + stats['diamond_dug']),
                'destruction': stats['dirt_dug'] + stats['sand_dug'] + stats['stone_dug']
            })
        
        # Sort by eco score (highest first)
        player_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Calculate column widths
        max_name_len = max(len(p['player']) for p in player_scores)
        max_name_len = max(max_name_len, len("Player"))
        max_rating_len = max(len(p['rating']) for p in player_scores)
        max_rating_len = max(max_rating_len, len("Rating"))
        
        # Header
        separator = "=" * (max_name_len + max_rating_len + 60)
        print("\n" + separator)
        print("ENVIRONMENTAL RESPONSIBILITY LEADERBOARD")
        print(separator)
        header = "{:<{}} | {:>10} | {:<{}} | {:>8} | {:>8} | {:>11}".format(
            "Player", max_name_len, "Eco Score", "Rating", max_rating_len, 
            "Farming", "Ores", "Destruction"
        )
        print(header)
        print(separator)
        
        # Display players
        for i, p in enumerate(player_scores, 1):
            # Add medal emoji for top 3
            rank = ""
            if i == 1:
                rank = "1st"
            elif i == 2:
                rank = "2nd"
            elif i == 3:
                rank = "3rd"
            else:
                rank = "{}th".format(i)
            
            row = "{:<{}} | {:>+10,} | {:<{}} | {:>8,} | {:>8,} | {:>11,}".format(
                p['player'], max_name_len, p['score'], p['rating'], max_rating_len,
                p['farming'], p['ores'], p['destruction']
            )
            
            # Highlight top 3 and bottom 3
            if i <= 3:
                print("*** " + row)
            elif i >= len(player_scores) - 2:
                print("!!! " + row)
            else:
                print("    " + row)
        
        print(separator)
        
        # Show scoring breakdown
        print("\nSCORING SYSTEM:")
        print("  Farming placed:     +10 points each (adds to world)")
        print("  Ores mined:         +2 points each (purposeful mining)")
        print("  Stone removed:      -1 point each (resource depletion)")
        print("  Dirt/Sand removed:  -2 points each (landscape destruction)")
        print("\n*** = Top 3 Most Responsible")
        print("!!! = Bottom 3 Most Destructive")
        print()
    
    def monitor(self):
        """Monitor the log file in real-time."""
        print("Starting Minetest monitor...")
        print("Tracking: stone, sand, dirt, ores (coal/copper/tin/iron/gold/diamond), farming")
        print("Stats saved to: {}".format(self.stats_file))
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
    LOG_FILE = "debug.txt"
    
    monitor = MinetestMonitor(LOG_FILE)
    
    # Example 1: Process existing log file (for testing)
    print("Choose mode:")
    print("1. Process existing log file (test mode)")
    print("2. Monitor log file in real-time")
    print("3. Show current stats table")
    print("4. Show environmental leaderboard")
    
    choice = input("\nEnter choice (1/2/3/4): ").strip()
    
    if choice == "1":
        # Test mode - process entire existing log
        clear = input("Clear existing stats? (y/n): ").strip().lower()
        monitor.process_existing_log(clear_stats=(clear == 'y'))
        monitor.print_table()
        print("\n" + "="*50)
        monitor.print_eco_leaderboard()
        
    elif choice == "2":
        # Real-time monitoring mode
        try:
            monitor.monitor()
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
            monitor.save_stats()
            monitor.print_table()
            print("\n" + "="*50)
            monitor.print_eco_leaderboard()
            print("\nStats saved to {}".format(monitor.stats_file))
    
    elif choice == "3":
        # Just display stats
        monitor.print_table()
    
    elif choice == "4":
        # Just display eco leaderboard
        monitor.print_eco_leaderboard()
    
    else:
        print("Invalid choice. Exiting.")
