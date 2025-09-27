# !/bin/bash

cmd="sqlite3 players.sqlite"
cmd1="select name from player;"
result=$($cmd "$cmd1")
echo $result

declare -A team_players=(
["team1"]="player1 2 3 4"
["team2"]="5 6 7"
["team3"]="8 9 10 11"
["team4"]="12 13 14 15"
["team5"]="16 17 18 19"
)


declare -A team_sums

for team in "${!team_players[@]}"; do
	players=(${team_players["$team"]})
	echo "way to go $team"
	coalN=0
	copperN=0
	tinN=0
	ironN=0
	goldN=0
	meseN=0
	diamondN=0
	for player in "${players[@]}"; do
		w="$player"
		
		list_coal="select item from player_inventory_items where player='$w' and item LIKE '%coal%';"
		coal_result=$($cmd "$list_coal")
		mapfile -t coal_lines <<< "$coal_result"
		for line in "${coal_lines[@]}"; do
			current_value=$(echo "$line" | awk '{print $NF}' | tr -d '\n')
			#echo "original output was $result"
			#echo "we got this value for coal $last_word"
			if [[ $current_value =~ ^[0-9]+$ ]]; then
				((coalN += current_value))
			fi
		done
	
			
		list_copper="select item from player_inventory_items where player='$w' and item LIKE '%copper%' and item NOT LIKE '%pick%' and item NOT LIKE '%sword%';"
	        copper_result=$($cmd "$list_copper")
		mapfile -t copper_lines <<< "$copper_result"
		for line in "${copper_lines[@]}"; do
			current_value=$(echo "$line" | awk '{print $NF}' | tr -d '\n')
			#echo "we got this value for copper $last_word"
			if [[ $current_value =~ ^[0-9]+$ ]]; then
				((copperN += current_value*2))
			fi
		done
	
		
		list_tin="select item from player_inventory_items where player='$w' and item LIKE '%tin%' and item NOT LIKE '%pick%' and item NOT LIKE '%sword%'";
		tin_result=$($cmd "$list_tin")
		mapfile -t tin_lines <<< "$tin_result"
		for line in "${tin_lines[@]}"; do
			current_value=$(echo "$line" | awk '{print $NF}' | tr -d '\n')
			#echo "we got this value for tin $last_word"
			if [[ $current_value =~ ^[0-9]+$ ]]; then
				((tinN += current_value*2))
			fi
		done

		
		list_iron="select item from player_inventory_items where player='$w' and item LIKE '%iron%' and item NOT LIKE '%pick%' and item NOT LIKE '%sword%';"
		iron_result=$($cmd "$list_iron")
		mapfile -t iron_lines <<< "$iron_result"
		for line in "${iron_lines[@]}"; do
			current_value=$(echo "$line" | awk '{print $NF}' | tr -d '\n')
			#echo "this is current: $current_value"
			if [[ $current_value =~ ^[0-9]+$ ]]; then
				((ironN += current_value*5))
				#echo "Updated ironN: $ironN"
			fi
		done

		
		list_gold="select item from player_inventory_items where player='$w' and item LIKE '%gold%' and item NOT LIKE '%pick%' and item NOT LIKE '%sword%';"
		gold_result=$($cmd "$list_gold")
		mapfile -t gold_lines <<< "$gold_result"
		for line in "${gold_lines[@]}"; do
			current_value=$(echo "$line" | awk '{print $NF}' | tr -d '\n')
			#echo "this is current $current_value"
			if [[ $current_value =~ ^[0-9]+$ ]]; then
				((goldN += current_value*10))
			fi
		done

		
		list_mese="select item from player_inventory_items where player='$w' and item LIKE '%mese%';"
		mese_result=$($cmd "$list_mese")
		mapfile -t mese_lines <<< "$mese_result"
		for line in "${mese_lines[@]}"; do
			current_value=$(echo "$line" | awk '{print $NF}' | tr -d '\n')
			if [[ $current_value =~ ^[0-9]+$ ]]; then
				((meseN += current_value*20))
			fi
		done

		
		list_diamond="select item from player_inventory_items where player='$w' and item LIKE '%diamond%' and item NOT LIKE '%pick%' and item NOT LIKE '%sword%' and item NOT LIKE '%axe%';"
		diamond_result=$($cmd "$list_diamond")
		mapfile -t diamond_lines <<< "$diamond_result"
		for line in "${diamond_lines[@]}"; do
			current_value=$(echo "$line" | awk '{print $NF}' | tr -d '\n')
			if [[ $current_value =~ ^[0-9]+$ ]]; then
				((diamondN += current_value*50))
			fi
		done
done

		echo "Sum of coal: $coalN"
		echo "sum of copper: $copperN"
		echo "sum of tin: $tinN"
		echo "sum of iron: $ironN"
		echo "sum of gold: $goldN"
		echo "sum of mese: $meseN"
		echo "sum of diamond: $diamondN"
		sum=$(echo "$coalN + $copperN + $tinN + $ironN + $goldN + $meseN + $diamondN" | bc)
		echo "$team total = $sum"
		team_sums["$team"]=$sum


done
echo "-----------------------------------"
echo "---------------totals--------------"
echo "-----------------------------------"

for team in $(echo "${!team_sums[@]}" | tr ' ' '\n' | sort -k2,2nr); do
	echo "Total sum for $team: ${team_sums["$team"]}"
done
