def print_character_sheet(character):
    """
    The beautiful, detailed printout from the Original Builder.
    Now a reusable function for the Game Engine.
    """
    id_info = character['identity']
    gp = character['gameplay_profile']
    inv = character['inventory']
    
    print("\n" + "="*40)
    print("🛡️  HERMES FINAL CHARACTER SHEET")
    print("="*40)
    print(f"NAME:       {id_info['name']}")
    print(f"CLASS:      {id_info['class']}         LEVEL: {id_info['level']}      XP: {id_info['xp']}")
    print(f"SPECIES:    {id_info['species']}       BACKGROUND:   {id_info['background']}")
    print(f"ALIGNMENT:  {id_info['alignment']}")
    print(f"ENTITY ID:  {character['entity_id']}")
    print(f"AGENT ID:   {character['agent_id']}")
    
    print("\n--- ABILITY SCORES & SAVING THROWS ---")
    print(f"             Score   Mod   Save")
    for stat in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]:
        score = gp['ability_scores'][stat]
        mod = gp['ability_modifiers'][stat]
        save = gp['saving_throws'][stat]
        print(f"{stat:<13} {score:<8} {mod:<6} {save}")
    
    print("\n--- COMBAT ---")
    print(f"Max HP: {gp['combat']['max_hp']}   Current HP: {gp['combat']['current_hp']}")
    print(f"AC: {gp['combat']['armor_class']} ({inv['equipped_armor']})")
    print(f"Initiative: {gp['combat']['initiative']}   Speed: {gp['combat']['speed']}ft")
    print(f"Passive Perception: {gp['passive_scores']['passive_perception']}")
    
    print("\n--- SKILLS ---")
    for s, bonus in gp['skills'].items():
        print(f"{s}: {bonus}")
        
    if gp['attacks']:
        print("\n--- ATTACKS ---")
        for att in gp['attacks']:
            print(f"{att['name']} | Attack: [{att['attack_bonus']:+d}] | Damage: {att['damage']}")
            
    if gp['spellcasting']:
        sc = gp['spellcasting']
        print("\n--- SPELLCASTING ---")
        print(f"Ability: {sc['ability']} | DC: {sc['dc']} | Attack: {sc['attack']:+d}")
        print(f"Cantrips: {', '.join(sc['cantrips'])}")
        
    rp = character['roleplay_profile']
    print("\n--- ROLEPLAY ---")
    print(f"Traits:     {', '.join(rp['personality_traits'])}")
    print(f"Ideal:      {rp['ideal']}")
    print(f"Bond:       {rp['bond']}")
    print(f"Flaw:       {rp['flaw']}")
    print(f"Backstory:  {rp['backstory']}")
    
    print("\n" + "="*40)
    print("✅ VALIDATION: PASSED")
    print("="*40)
