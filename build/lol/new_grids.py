"""Legend of Link: the new first-quest level shapes (the user's maps). Rows A-H, columns 1-16; a digit is that
level's room, '.' none. Hidden rooms (left off the level map) are in HIDDEN; entrances in ENTRANCES."""
LEVELS_1_6 = [".114444455665566",
              "1..1444535555356",
              ".22124.533333356",
              ".2112..553333556",
              ".2122.4553333556",
              ".212244455335566",
              "22..444445555666",
              "2214444444553366"]
LEVELS_7_9 = [".87888779...99.9",
              ".878887799999..9",
              ".8778.889.9.9999",
              "8888888899999999",
              "78778.889.9.9.9.",
              "7.7888779...9.9.",
              "7.78.87799.99.99",
              "7778.877.999.999"]
HIDDEN = {1: ["A1", "G3"], 9: ["C10", "C12"]}
for lv, rooms in HIDDEN.items():
    for r in rooms:
        grid = LEVELS_1_6 if lv <= 6 else LEVELS_7_9
        row, col = "ABCDEFGH".index(r[0]), int(r[1:]) - 1
        grid[row] = grid[row][:col] + str(lv) + grid[row][col + 1:]
ENTRANCES = {1: "H3", 2: "H1", 3: "H14", 4: "H7", 5: "H11", 6: "H16", 7: "H2", 8: "H6", 9: "H16"}
TRANSPORTS = {1: [("B4", "A3")], 2: [("F2", "C5")], 3: [("H13", "D12")], 4: [("E7", "C6")],
              5: [("D14", "A13"), ("C8", "B11")], 6: [("G14", "A12")]}
SPECIAL = {9: {"Ganon": "B16", "Zelda": "A16"}}
