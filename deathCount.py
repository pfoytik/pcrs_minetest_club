# -*- coding: utf-8 -*-
import re
import time
import json
from collections import defaultdict

class MinetestDeathTracker:
    def __init__(self, log_file_path, stats_file='minetest_deaths.json'):
        self.log_file_path = log_file_path
        self.stats_file = stats_file
        self.stats = self.load_stats()
        # Track recent damage for each player to determine death cause
        self.recent_damage = {}
    
    def load_stats(self):
        """Load existing death stats from file or create new."""
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
        """Initialize a new player's death stats."""
        if player not in self.stats:
            self.stats[player] = {
                'total_deaths': 0,
                'death_causes': {}
            }
    
    def extract_damage_info(self, line):
        """Extract damage information from damage log lines."""
        # Pattern 1: "ACTION[Server]: player damaged by X hp at (coords)"
        damage_pattern = r'ACTION\[Server\]: (\w+) damaged by (\d+) hp'
        match = re.search(damage_pattern, line)
        
        if match:
            player = match.group(1)
            damage = int(match.group(2))
            
            # Try to determine damage type from the line or context
            cause = self.determine_damage_cause(line, damage)
            
            # Store recent damage for this player
            self.recent_damage[player] = cause
            
            return player, damage, cause
        
        # Pattern 2: "LuaEntitySAO ... punched player X"
        punch_pattern = r'punched player (\w+).*damage=(\d+)'
        match = re.search(punch_pattern, line)
        
        if match:
            player = match.group(1)
            damage = int(match.group(2))
            
            # Determine what punched the player
            cause = self.determine_punch_cause(line)
            
            # Store recent damage for this player
            self.recent_damage[player] = cause
            
            return player, damage, cause
        
        return None, None, None
    
    def determine_punch_cause(self, line):
        """Determine the cause when player is punched by an entity."""
        # Extract entity name from the line
        entity_pattern = r'LuaEntitySAO "([^"]+)"'
        match = re.search(entity_pattern, line)
        
        if match:
            entity = match.group(1)
            
            # Check for specific mob types
            if 'arrow' in entity.lower():
                return 'Arrow/Projectile'
            elif 'monster' in entity.lower():
                return 'Monster'
            elif 'zombie' in entity.lower():
                return 'Zombie'
            elif 'spider' in entity.lower():
                return 'Spider'
            elif 'skeleton' in entity.lower():
                return 'Skeleton'
            elif 'creeper' in entity.lower():
                return 'Creeper'
            elif 'slime' in entity.lower():
                return 'Slime'
            else:
                # Return the entity type if it's not recognized
                return 'Mob ({})'.format(entity.split(':')[-1] if ':' in entity else entity)
        
        # Check if another player punched them
        if 'punched player' in line:
            return 'Player Attack'
        
        return 'Mob/Entity'
    
    def determine_damage_cause(self, line, damage):
        """Determine the cause of damage based on context."""
        # Check for specific keywords in the damage line
        line_lower = line.lower()
        
        # Very high damage usually indicates fall
        if damage >= 15:
            return 'Fall Damage'
        
        # Check for specific keywords
        if 'drown' in line_lower:
            return 'Drowning'
        elif 'lava' in line_lower:
            return 'Lava'
        elif 'fire' in line_lower or 'burn' in line_lower:
            return 'Fire'
        elif 'suffocate' in line_lower or 'suffocation' in line_lower:
            return 'Suffocation'
        elif 'punch' in line_lower or 'mob' in line_lower:
            return 'Mob/Player'
        
        # Medium-high damage (10-14) is likely fall
        elif damage >= 10:
            return 'Fall Damage'
        
        # Low damage could be drowning, fire, or environmental
        elif damage <= 3:
            return 'Environmental'
        
        return 'Unknown'
    
    def parse_and_update(self, line, verbose=True):
        """Parse log line and update death stats if relevant."""
        # First, check for damage events (both types)
        player, damage, cause = self.extract_damage_info(line)
        if player:
            # Just store the damage cause, don't print yet
            return False
        
        # Pattern for player deaths
        death_pattern = r'ACTION\[Server\]: (\w+) dies at'
        death_match = re.search(death_pattern, line)
        
        if death_match:
            player = death_match.group(1)
            self.init_player(player)
            
            # Increment total deaths
            self.stats[player]['total_deaths'] += 1
            
            # Use the most recent damage cause for this player
            if player in self.recent_damage:
                cause = self.recent_damage[player]
            else:
                cause = 'Unknown'
            
            # Track death causes
            if cause in self.stats[player]['death_causes']:
                self.stats[player]['death_causes'][cause] += 1
            else:
                self.stats[player]['death_causes'][cause] = 1
            
            if verbose:
                print("[DEATH] {} died! Total: {} (Cause: {})".format(
                    player, 
                    self.stats[player]['total_deaths'],
                    cause
                ))
            
            return True
        
        return False
    
    def process_existing_log(self, clear_stats=False):
        """Process entire existing log file."""
        if clear_stats:
            self.stats = {}
            print("Cleared existing death stats.")
        
        # Reset recent damage tracking
        self.recent_damage = {}
        
        print("Processing existing log: {}".format(self.log_file_path))
        print("Counting player deaths...")
        print("-" * 50)
        
        line_count = 0
        death_count = 0
        
        try:
            with open(self.log_file_path, 'r') as log_file:
                for line in log_file:
                    line_count += 1
                    if self.parse_and_update(line.strip(), verbose=False):
                        death_count += 1
                    
                    # Progress indicator every 1000 lines
                    if line_count % 1000 == 0:
                        print("Processed {} lines, found {} deaths...".format(line_count, death_count))
        
            print("\n[+] Processing complete!")
            print("  Total lines processed: {}".format(line_count))
            print("  Total deaths found: {}".format(death_count))
            
            self.save_stats()
            print("  Stats saved to: {}".format(self.stats_file))
            
        except IOError:
            print("Error: Log file not found at {}".format(self.log_file_path))
        except Exception as e:
            print("Error processing log: {}".format(e))
    
    def print_death_table(self):
        """Print death statistics in a table."""
        if not self.stats:
            print("\nNo death statistics available yet.\n")
            return
        
        # Sort by total deaths (most deaths first)
        sorted_players = sorted(
            self.stats.items(),
            key=lambda x: x[1]['total_deaths'],
            reverse=True
        )
        
        # Calculate column widths
        max_name_len = max(len(player) for player in self.stats.keys())
        max_name_len = max(max_name_len, len("Player"))
        
        # Header
        separator = "=" * (max_name_len + 50)
        print("\n" + separator)
        print("PLAYER DEATH STATISTICS")
        print(separator)
        header = "{:<{}} | {:>12} | {:<30}".format(
            "Player", max_name_len, "Total Deaths", "Most Common Cause"
        )
        print(header)
        print(separator)
        
        total_deaths = 0
        
        for player, stats in sorted_players:
            deaths = stats['total_deaths']
            total_deaths += deaths
            
            # Find most common death cause
            if stats['death_causes']:
                most_common = max(stats['death_causes'].items(), key=lambda x: x[1])
                cause_text = "{} ({})".format(most_common[0], most_common[1])
            else:
                cause_text = "N/A"
            
            row = "{:<{}} | {:>12,} | {:<30}".format(
                player, max_name_len, deaths, cause_text
            )
            print(row)
        
        # Footer
        print(separator)
        print("Total Deaths: {:,}".format(total_deaths))
        print("Total Players: {}".format(len(self.stats)))
        print(separator)
        print()
    
    def print_detailed_stats(self):
        """Print detailed death statistics for each player."""
        if not self.stats:
            print("\nNo death statistics available yet.\n")
            return
        
        # Sort by total deaths
        sorted_players = sorted(
            self.stats.items(),
            key=lambda x: x[1]['total_deaths'],
            reverse=True
        )
        
        print("\n" + "=" * 60)
        print("DETAILED DEATH STATISTICS")
        print("=" * 60)
        
        for player, stats in sorted_players:
            print("\n{} - {} total deaths".format(player, stats['total_deaths']))
            print("-" * 40)
            
            if stats['death_causes']:
                # Sort death causes by frequency
                sorted_causes = sorted(
                    stats['death_causes'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                
                for cause, count in sorted_causes:
                    percentage = (count / stats['total_deaths']) * 100
                    print("  {:<20} : {:>3} ({:.1f}%)".format(cause, count, percentage))
            else:
                print("  No death causes recorded")
        
        print("\n" + "=" * 60)
        print()
    
    def print_survival_leaderboard(self):
        """Print leaderboard showing who survives best (fewest deaths)."""
        if not self.stats:
            print("\nNo death statistics available yet.\n")
            return
        
        # Sort by fewest deaths (best survivors first)
        sorted_players = sorted(
            self.stats.items(),
            key=lambda x: x[1]['total_deaths']
        )
        
        max_name_len = max(len(player) for player in self.stats.keys())
        max_name_len = max(max_name_len, len("Player"))
        
        separator = "=" * (max_name_len + 40)
        print("\n" + separator)
        print("SURVIVAL LEADERBOARD (Fewest Deaths)")
        print(separator)
        header = "{:<6} {:<{}} | {:>12}".format(
            "Rank", "Player", max_name_len, "Deaths"
        )
        print(header)
        print(separator)
        
        for i, (player, stats) in enumerate(sorted_players, 1):
            deaths = stats['total_deaths']
            
            # Add medals for top 3
            if i == 1:
                rank_str = "*** 1"
            elif i == 2:
                rank_str = "*** 2"
            elif i == 3:
                rank_str = "*** 3"
            else:
                rank_str = "    {}".format(i)
            
            row = "{:<6} {:<{}} | {:>12,}".format(
                rank_str, player, max_name_len, deaths
            )
            print(row)
        
        print(separator)
        print("\n*** = Top 3 Survivors (Fewest Deaths)")
        print()
    
    def monitor(self):
        """Monitor the log file in real-time for deaths."""
        print("Starting Minetest death monitor...")
        print("Tracking player deaths in real-time")
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
                    
                    # Save stats every 5 deaths to avoid excessive disk writes
                    if save_counter >= 5:
                        self.save_stats()
                        save_counter = 0

# Usage
if __name__ == "__main__":
    # Replace with your actual log file path
    LOG_FILE = "/path/to/minetest/debug.txt"
    
    tracker = MinetestDeathTracker(LOG_FILE)
    
    print("Minetest Death Tracker")
    print("=" * 50)
    print("Choose mode:")
    print("1. Process existing log file")
    print("2. Monitor log file in real-time")
    print("3. Show death statistics table")
    print("4. Show detailed death statistics")
    print("5. Show survival leaderboard")
    
    choice = input("\nEnter choice (1/2/3/4/5): ").strip()
    
    if choice == "1":
        # Process existing log
        clear = input("Clear existing stats? (y/n): ").strip().lower()
        tracker.process_existing_log(clear_stats=(clear == 'y'))
        tracker.print_death_table()
        
    elif choice == "2":
        # Real-time monitoring
        try:
            tracker.monitor()
        except KeyboardInterrupt:
            print("\n\nStopping death monitor...")
            tracker.save_stats()
            tracker.print_death_table()
            print("\nStats saved to {}".format(tracker.stats_file))
    
    elif choice == "3":
        # Show death table
        tracker.print_death_table()
    
    elif choice == "4":
        # Show detailed stats
        tracker.print_detailed_stats()
    
    elif choice == "5":
        # Show survival leaderboard
        tracker.print_survival_leaderboard()
    
    else:
        print("Invalid choice. Exiting.")
