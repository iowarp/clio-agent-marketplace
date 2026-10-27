# The board wall

`BoardWall` shows every game of a study as a small board of letter tiles, coloured
correct, present or absent, grouped by the branch that played it, above a tally of
games played, mean guesses of solved games and failures per branch.

You do not build this surface. The wall fills itself: each `new_game` and `guess`
result carries the game's tiles to the UI, so games appear as they are played. Do
not narrate games to make them visible.
