# The bench readings view

`Readings` shows every reading a study has taken, seconds per cycle against each of
the four inputs, coloured by the branch that took it.

Beside the readings it draws the study's current law as open diamonds (its
"shadow"): the most recent hypothesis that still stands and whose `formula` is
written in the readings' own names, `ten_cycles_s = <expression>` or
`period_s = <expression>`, reading only `arm_length_m`, `bob_mass_kg`,
`release_angle_deg` and `ambient_temp_c`. A wrong law drifts away from the
readings; a right one settles onto them. A formula in other names draws nothing.

You do not build this surface. It fills itself: each `measure` result carries its
readings to the UI. Fit and compare laws in your own analysis and charts.
