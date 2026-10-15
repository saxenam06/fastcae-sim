# baseline2_lw8: features and members

From the run `topofree_mass_tilt_7.73kg_4mm_projected_band24_cup_bolts_split_contract_drive_baseline2_lw8_empty_shell_notowers_protect_modes12_fm500_hf4_single_p40_max16_flange_beds_lm8_lw8_sf1.5` (4 mm columns).

## The cover

| Feature | Of | Where (mm) | Size (mm) |
|---|---|---|---|
| bearing boss | input +z | [-82.9, 0.0] | diameter 75.0, bore 52.0, z [14.4, 40.0] |
| bearing boss | intermediate +z | [0.0, 0.0] | diameter 122.5, bore 90.0, z [14.4, 84.5] |
| bearing boss | output +z | [28.4, 121.8] | diameter 116.2, bore 85.0, z [14.4, 80.1] |
| bolt bosses | 13 |  | diameter 20.0, thickness 8.0 |
| sealing land |  |  | width 10.0, thickness 8.0 |

| Member | Kind | Along (mm, from → to) | Length | Width | Height off the wall (median / most) | Shape | Meets |
|---|---|---|---|---|---|---|---|
| C1 | gusset | [-117.7, -24.7] → [-129.4, -29.6] | 16.6 | 6.7 | 24.0 / 24.0 | straight | input +z and bolts' bosses |
| C2 | rib | [-24.4, 50.5] → [-90.1, 64.9] | 71.3 | 13.0 | 34.0 / 56.0 | curved | intermediate +z and bolts' bosses |
| C3 | rib | [-30.0, 109.1] → [-70.3, 110.9] | 44.3 | 7.9 | 24.0 / 32.0 | straight | output +z |
| C4 | web | [-28.0, 142.0] → [-69.6, 157.9] | 48.5 | 14.2 | 24.0 / 40.0 | straight | output +z |
| C5 | rib | [-22.8, -57.3] → [-59.5, -66.2] | 41.8 | 10.3 | 20.0 / 44.0 | straight | intermediate +z and bolts' bosses |
| C6 | gusset | [-1.9, 66.9] → [-14.1, 64.0] | 16.6 | 5.8 | 32.0 / 32.0 | straight | intermediate +z and output +z |
| C7 | gusset | [6.1, -64.5] → [-7.1, -68.8] | 17.9 | 8.9 | 24.0 / 36.0 | straight | intermediate +z and bolts' bosses |
| C8 | gusset | [57.9, -39.8] → [47.7, -46.5] | 16.2 | 6.9 | 44.0 / 52.0 | straight | intermediate +z and bolts' bosses |
| C9 | network | [55.2, -10.2] → [105.8, 50.4] | 82.9 | 17.4 | 24.0 / 64.0 | branched (4 ends) | intermediate +z and bolts' bosses |
| C10 | rib | [145.1, 91.7] → [149.0, 132.4] | 45.0 | 8.5 | 24.0 / 40.0 | curved | bolts' bosses |

The designer's reading: each member's straight runs (`runs_of`), with each run's width and heights off the wall. Draw a rib's, a web's or a gusset's run at its deep height; an arm or a network as the field has it.

| Member | Draw | Run | From (mm) | To (mm) | Length | Width | Deep height | Height at its start / middle / end |
|---|---|---|---|---|---|---|---|---|
| C1 | straight, deep height | 1 | [-130.2, -27.6] | [-122.2, -27.6] | 8.0 | 9.3 | 24.0 | 16.0 / 24.0 / 24.0 |
| C1 | straight, deep height | 2 | [-122.2, -27.6] | [-112.8, -21.0] | 11.5 | 9.3 | 24.0 | 24.0 / 24.0 / 24.0 |
| C2 | straight, deep height | 1 | [-90.2, 64.4] | [-78.2, 64.4] | 12.0 | 7.0 | 52.0 | 40.0 / 48.0 / 48.0 |
| C2 | straight, deep height | 2 | [-74.2, 60.4] | [-66.2, 56.4] | 8.9 | 11.1 | 52.8 | 52.0 / 48.0 / 46.0 |
| C2 | straight, deep height | 3 | [-74.2, 64.4] | [-62.2, 60.4] | 12.6 | 10.6 | 24.0 | 20.0 / 20.0 / 24.0 |
| C2 | straight, deep height | 4 | [-58.2, 56.4] | [-22.2, 60.4] | 36.2 | 12.3 | 36.0 | 24.0 / 32.0 / 36.0 |
| C2 | straight, deep height | 5 | [-88.4, 64.4] | [-88.4, 70.3] | 5.9 | 7.0 | 52.0 | 41.2 / 41.2 / 41.2 |
| C3 | straight, deep height | 1 | [-66.2, 108.4] | [-34.2, 108.4] | 32.0 | 9.8 | 32.0 | 20.0 / 24.0 / 28.0 |
| C3 | straight, deep height | 2 | [-34.2, 108.4] | [-27.4, 109.8] | 6.9 | 9.8 | 32.0 | 28.0 / 28.0 / 28.0 |
| C4 | straight, deep height | 1 | [-70.2, 156.4] | [-30.2, 148.4] | 40.8 | 15.4 | 36.0 | 20.0 / 24.0 / 28.0 |
| C5 | straight, deep height | 1 | [-58.2, -71.6] | [-42.2, -59.6] | 20.0 | 11.3 | 21.6 | 8.0 / 20.0 / 20.0 |
| C5 | straight, deep height | 2 | [-42.2, -59.6] | [-22.2, -59.6] | 20.0 | 6.7 | 40.4 | 40.0 / 36.0 / 28.0 |
| C6 | straight, deep height | 1 | [-14.2, 64.4] | [-6.2, 64.4] | 8.0 | 8.0 | 32.0 | 28.0 / 32.0 / 32.0 |
| C6 | straight, deep height | 2 | [-6.2, 64.4] | [-1.1, 72.9] | 9.9 | 8.0 | 32.0 | 32.0 / 32.0 / 32.0 |
| C7 | straight, deep height | 1 | [-6.2, -67.6] | [1.8, -67.6] | 8.0 | 13.3 | 36.0 | 20.0 / 24.0 / 24.0 |
| C8 | straight, deep height | 1 | [45.8, -43.6] | [53.8, -43.6] | 8.0 | 9.3 | 47.2 | 52.0 / 44.0 / 36.0 |
| C8 | straight, deep height | 2 | [53.8, -43.6] | [60.2, -44.3] | 6.4 | 9.3 | 47.2 | 36.0 / 36.0 / 36.0 |
| C9 | as the field | 1 | [57.8, 32.4] | [65.8, 28.4] | 8.9 | 9.9 | 48.0 | 48.0 / 38.0 / 36.0 |
| C9 | as the field | 2 | [61.8, -15.6] | [73.8, 4.4] | 23.3 | 11.1 | 56.0 | 56.0 / 40.0 / 32.0 |
| C9 | as the field | 3 | [69.8, 24.4] | [73.8, 12.4] | 12.6 | 11.5 | 32.0 | 24.0 / 28.0 / 28.0 |
| C9 | as the field | 4 | [73.8, 28.4] | [101.8, 40.4] | 30.5 | 13.0 | 24.0 | 24.0 / 24.0 / 20.0 |
| C9 | as the field | 5 | [101.8, 40.4] | [113.8, 36.4] | 12.6 | 8.6 | 12.0 | 12.0 / 12.0 / 12.0 |
| C9 | as the field | 6 | [77.8, 8.4] | [89.8, 8.4] | 12.0 | 14.0 | 40.0 | 30.0 / 36.0 / 36.0 |
| C10 | straight, deep height | 1 | [137.8, 92.4] | [145.8, 100.4] | 11.3 | 8.4 | 32.0 | 28.0 / 30.0 / 32.0 |
| C10 | straight, deep height | 2 | [145.8, 100.4] | [145.8, 132.4] | 32.0 | 7.1 | 40.0 | 12.0 / 18.0 / 40.0 |

## The motor side

| Feature | Of | Where (mm) | Size (mm) |
|---|---|---|---|
| bearing boss | input -z | [-82.9, 0.0] | diameter 135.0, bore 100.0, z [-50.0, 14.4] |
| bearing boss | intermediate -z | [0.0, 0.0] | diameter 75.0, bore 52.0, z [-40.7, 14.4] |
| bearing boss | output -z | [28.4, 121.8] | diameter 135.0, bore 100.0, z [-45.9, 14.4] |
| bolt bosses | 13 |  | diameter 20.0, thickness 8.0 |
| sealing land |  |  | width 10.0, thickness 8.0 |
| mount lug | mount-1 | [-170.2, -52.7] | diameter 36.0, z [-49.0, -19.0] |
| mount lug | mount-2 | [176.4, 62.9] | diameter 36.0, z [-49.0, -19.0] |
| mount lug | mount-3 | [35.1, 280.9] | diameter 36.0, z [-49.0, -19.0] |

| Member | Kind | Along (mm, from → to) | Length | Width | Height off the wall (median / most) | Shape | Meets |
|---|---|---|---|---|---|---|---|
| M1 | arm | [-155.2, -44.4] → [-163.8, 8.8] | 57.9 | 11.1 | 54.0 / 72.0 | straight | input -z and mount-1 and bolts' bosses |
| M2 | rib | [-99.8, 71.5] → [-122.0, 60.1] | 29.0 | 5.5 | 40.0 / 48.0 | straight | input -z and bolts' bosses |
| M3 | rib | [-39.8, 116.9] → [-79.8, 89.0] | 52.8 | 8.8 | 24.0 / 52.0 | straight | output -z and bolts' bosses |
| M4 | rib | [-38.1, 145.0] → [-79.6, 154.3] | 46.5 | 12.0 | 24.0 / 60.0 | straight | output -z and bolts' bosses |
| M5 | gusset | [-67.8, 67.4] → [-75.0, 79.9] | 18.4 | 6.1 | 48.0 / 56.0 | straight | input -z and bolts' bosses |
| M6 | rib | [-9.5, -81.2] → [-56.9, -67.1] | 53.4 | 12.3 | 24.0 / 36.0 | straight | input -z and bolts' bosses |
| M7 | gusset | [-30.2, -59.6] → [-36.2, -53.6] | 12.5 | 7.7 | 28.0 / 40.0 | straight | input -z |
| M8 | web | [-4.8, 61.6] → [-32.1, 48.2] | 34.5 | 13.9 | 24.0 / 36.0 | straight | input -z and output -z |
| M9 | arm | [80.0, 269.7] → [-21.1, 212.6] | 120.1 | 16.1 | 36.0 / 80.0 | curved | output -z and mount-3 and bolts' bosses |
| M10 | web | [57.7, -23.7] → [44.9, 14.7] | 44.5 | 18.0 | 20.0 / 28.0 | straight | intermediate -z |
| M11 | rib | [75.3, -24.3] → [91.4, 11.6] | 43.4 | 8.5 | 12.0 / 12.0 | straight | bolts' bosses |
| M12 | arm | [175.4, 33.7] → [76.9, 69.8] | 108.9 | 24.5 | 32.0 / 64.0 | branched (5 ends) | output -z and mount-2 and bolts' bosses |

The designer's reading: each member's straight runs (`runs_of`), with each run's width and heights off the wall. Draw a rib's, a web's or a gusset's run at its deep height; an arm or a network as the field has it.

| Member | Draw | Run | From (mm) | To (mm) | Length | Width | Deep height | Height at its start / middle / end |
|---|---|---|---|---|---|---|---|---|
| M1 | as the field | 1 | [-162.2, 4.4] | [-166.2, -15.6] | 20.4 | 13.1 | 60.0 | 40.0 / 50.0 / 56.0 |
| M1 | as the field | 2 | [-166.2, -15.6] | [-150.2, -43.6] | 32.2 | 8.8 | 64.8 | 56.0 / 56.0 / 34.0 |
| M1 | as the field | 3 | [-162.2, 4.4] | [-149.3, 3.7] | 12.9 | 13.1 | 60.0 | 40.0 / 40.0 / 40.0 |
| M1 | as the field | 4 | [-151.2, -41.8] | [-155.4, -44.3] | 4.9 | 8.8 | 64.8 | 35.4 / 35.4 / 35.4 |
| M2 | straight, deep height | 1 | [-122.2, 60.4] | [-102.2, 68.4] | 21.5 | 6.3 | 48.0 | 48.0 / 40.0 / 40.0 |
| M2 | straight, deep height | 2 | [-109.1, 65.6] | [-107.6, 61.7] | 4.2 | 6.3 | 48.0 | 42.8 / 42.8 / 42.8 |
| M2 | straight, deep height | 3 | [-102.2, 68.4] | [-95.5, 73.7] | 8.6 | 6.3 | 48.0 | 40.0 / 40.0 / 40.0 |
| M3 | straight, deep height | 1 | [-82.2, 92.4] | [-70.2, 92.4] | 12.0 | 6.0 | 22.0 | 12.0 / 16.0 / 20.0 |
| M3 | straight, deep height | 2 | [-70.2, 92.4] | [-42.2, 120.4] | 39.6 | 8.4 | 47.2 | 24.0 / 28.0 / 44.0 |
| M3 | straight, deep height | 3 | [-82.2, 92.4] | [-84.6, 87.5] | 5.5 | 6.0 | 22.0 | 12.0 / 12.0 / 12.0 |
| M4 | straight, deep height | 1 | [-78.2, 160.4] | [-66.2, 148.4] | 17.0 | 10.7 | 24.0 | 16.0 / 20.0 / 24.0 |
| M4 | straight, deep height | 2 | [-66.2, 148.4] | [-42.2, 144.4] | 24.3 | 11.9 | 56.0 | 24.0 / 40.0 / 54.0 |
| M4 | straight, deep height | 3 | [-42.2, 144.4] | [-34.9, 142.1] | 7.6 | 11.9 | 56.0 | 54.0 / 54.0 / 54.0 |
| M5 | straight, deep height | 1 | [-74.2, 80.4] | [-70.2, 68.4] | 12.6 | 6.7 | 56.0 | 28.0 / 48.0 / 56.0 |
| M5 | straight, deep height | 2 | [-74.2, 80.4] | [-79.5, 80.0] | 5.3 | 6.7 | 56.0 | 28.0 / 28.0 / 28.0 |
| M6 | straight, deep height | 1 | [-58.2, -71.6] | [-14.2, -83.6] | 45.6 | 13.2 | 36.0 | 34.0 / 24.0 / 24.0 |
| M6 | straight, deep height | 2 | [-58.2, -71.6] | [-61.2, -62.9] | 9.2 | 13.2 | 36.0 | 34.0 / 34.0 / 34.0 |
| M6 | straight, deep height | 3 | [-14.2, -83.6] | [-6.1, -83.1] | 8.2 | 13.2 | 36.0 | 24.0 / 24.0 / 24.0 |
| M7 | straight, deep height | 1 | [-30.2, -59.6] | [-36.2, -53.6] | 8.5 | 7.7 | 36.0 | 20.0 / 28.0 / 32.0 |
| M8 | straight, deep height | 1 | [-26.2, 40.4] | [-18.2, 56.4] | 17.9 | 14.6 | 28.0 | 26.0 / 24.0 / 24.0 |
| M8 | straight, deep height | 2 | [-18.2, 56.4] | [-6.2, 56.4] | 12.0 | 10.0 | 36.0 | 28.0 / 28.0 / 26.0 |
| M8 | straight, deep height | 3 | [-6.2, 56.4] | [-2.7, 63.0] | 7.5 | 10.0 | 36.0 | 26.0 / 26.0 / 26.0 |
| M9 | as the field | 1 | [9.8, 192.4] | [-10.2, 204.4] | 23.3 | 10.0 | 48.0 | 48.0 / 40.0 / 24.0 |
| M9 | as the field | 2 | [-10.2, 204.4] | [-10.2, 216.4] | 12.0 | 7.0 | 24.0 | 24.0 / 24.0 / 24.0 |
| M9 | as the field | 3 | [-10.2, 216.4] | [17.8, 260.4] | 52.2 | 11.7 | 48.0 | 24.0 / 36.0 / 48.0 |
| M9 | as the field | 4 | [17.8, 260.4] | [41.8, 256.4] | 24.3 | 5.1 | 28.8 | 16.0 / 16.0 / 20.0 |
| M9 | as the field | 5 | [41.8, 256.4] | [69.8, 272.4] | 32.2 | 8.4 | 80.0 | 14.0 / 48.0 / 76.0 |
| M9 | as the field | 6 | [69.8, 272.4] | [89.8, 232.4] | 44.7 | 9.2 | 64.0 | 56.0 / 36.0 / 28.0 |
| M9 | as the field | 7 | [9.8, 192.4] | [11.5, 186.1] | 6.5 | 10.0 | 48.0 | 48.0 / 48.0 / 48.0 |
| M9 | as the field | 8 | [47.3, 259.5] | [43.5, 266.1] | 7.6 | 8.4 | 80.0 | 26.2 / 26.2 / 26.2 |
| M10 | straight, deep height | 1 | [37.8, 12.4] | [45.8, 4.4] | 11.3 | 7.3 | 28.0 | 20.0 / 28.0 / 28.0 |
| M10 | straight, deep height | 2 | [45.8, -7.6] | [57.8, -11.6] | 12.6 | 28.8 | 28.0 | 28.0 / 20.0 / 16.0 |
| M10 | straight, deep height | 3 | [49.8, -3.6] | [49.8, 4.4] | 8.0 | 17.3 | 26.4 | 28.0 / 16.0 / 18.0 |
| M11 | straight, deep height | 1 | [73.8, -23.6] | [85.8, 8.4] | 34.2 | 9.6 | 12.0 | 12.0 / 12.0 / 12.0 |
| M11 | straight, deep height | 2 | [85.8, 8.4] | [93.5, 14.7] | 9.9 | 9.6 | 12.0 | 12.0 / 12.0 / 12.0 |
| M12 | as the field | 1 | [81.8, 20.4] | [93.8, 36.4] | 20.0 | 7.3 | 24.0 | 12.0 / 16.0 / 16.0 |
| M12 | as the field | 2 | [85.8, 80.4] | [81.8, 68.4] | 12.6 | 6.7 | 56.0 | 56.0 / 56.0 / 56.0 |
| M12 | as the field | 3 | [81.8, 68.4] | [93.8, 36.4] | 34.2 | 13.0 | 44.0 | 40.0 / 24.0 / 24.0 |
| M12 | as the field | 4 | [93.8, 36.4] | [125.8, 20.4] | 35.8 | 9.3 | 32.0 | 16.0 / 28.0 / 32.0 |
| M12 | as the field | 5 | [125.8, 20.4] | [161.8, 32.4] | 37.9 | 8.8 | 54.4 | 32.0 / 32.0 / 48.0 |
| M12 | as the field | 6 | [97.8, 108.4] | [121.8, 96.4] | 26.8 | 8.3 | 52.0 | 52.0 / 44.0 / 40.0 |
| M12 | as the field | 7 | [121.8, 96.4] | [145.8, 64.4] | 40.0 | 6.5 | 48.0 | 40.0 / 40.0 / 48.0 |
| M12 | as the field | 8 | [149.8, 60.4] | [161.8, 40.4] | 23.3 | 12.3 | 64.0 | 48.0 / 52.0 / 52.0 |
| M12 | as the field | 9 | [149.8, 64.4] | [165.8, 80.4] | 22.6 | 5.4 | 32.0 | 18.0 / 4.0 / 4.0 |
| M12 | as the field | 10 | [165.8, 36.4] | [173.8, 40.4] | 8.9 | 9.9 | 64.0 | 64.0 / 60.0 / 36.0 |
| M12 | as the field | 11 | [162.3, 77.0] | [164.4, 74.9] | 2.9 | 5.4 | 32.0 | 7.0 / 7.0 / 7.0 |
