# create a dictionary of statute info and offense type 
# key: (title, chapter)

offense_dict = {}
### Unknown statute
offense_dict[(0,0)] = 'unknown statute'

### title 18

# Inchoate crimes
offense_dict[(18,9)] = 'inchoate crimes'
# against government
offense_dict[(18,21)] = 'offenses against the flag'
# danger to person
offense_dict[(18,25)] = 'criminal homicide'
offense_dict[(18,26)] = 'crimes against unborn child'
offense_dict[(18,27)] = 'assault'
offense_dict[(18,28)] = 'antihazing'
offense_dict[(18,29)] = 'kidnapping'
offense_dict[(18,30)] = 'human trafficking'
offense_dict[(18,31)] = 'sexual offenses'
offense_dict[(18,32)] = 'abortion'
# offenses against property
offense_dict[(18,33)] = 'arson, criminal mischief, and other property destruction'
offense_dict[(18,35)] = 'burglary and other criminal intrusion'
offense_dict[(18,37)] = 'robbery'
offense_dict[(18,39)] = 'theft and related offenses'
offense_dict[(18,41)] = 'forgery and fraudulent practices'
# offenses against family
offense_dict[(18,43)] = 'offenses against the family'
# offenses against public administration
offense_dict[(18,47)] = 'bribery and corrupt influence'
offense_dict[(18,49)] = 'falsification and intimidation'
offense_dict[(18,51)] = 'obstructing governmental operations'
offense_dict[(18,53)] = 'abuse of office'
# offenses against public order and decency
offense_dict[(18,55)] = 'riot, disorderly conduct and related offenses'
offense_dict[(18,57)] = 'wiretapping and electronic surveillance'
offense_dict[(18,59)] = 'public indecency'
# miscellaneous offenses
offense_dict[(18,61)] = 'firearms and other dangerous articles'
offense_dict[(18,63)] = 'minors'
offense_dict[(18,65)] = 'nuisances'
offense_dict[(18,67)] = 'proprietary and official rights'
offense_dict[(18,69)] = 'public utilities'
offense_dict[(18,71)] = 'sports and amusemenets'
offense_dict[(18,73)] = 'trade and commerce'
offense_dict[(18,75)] = 'other offenses'
offense_dict[(18,76)] = 'computer offense'
offense_dict[(18,77)] = 'vehicle chop shop and illegally obtained and altered property'

### title 23
offense_dict[(23,61)] = 'domestic relations and abuse'

### title 35
offense_dict[(35,780)] = 'drug and substance'

### title 42 Judiciary 7 judicial procedure
offense_dict[(42,91)] = 'arrest prior to requisition'

### title 75: traffic laws
offense_dict[(75,1)] = 'general traffic offense'
offense_dict[(75,2)] = 'serious traffic offense'
offense_dict[(75,3)] = 'accidents report'
offense_dict[(75,38)] = 'driving after imbibing alcohol or utilizing drugs'
offense_dict[(75,43)] = 'vehicles: lighting equipment'
offense_dict[(75,45)] = 'vehicles: other required equipment'