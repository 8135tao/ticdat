Repository for `amplpy` examples.

---

**Watch out** 

**tl/dr** *When it comes to Python integration, AMPL is close but not quite there. I don't recommend it*

While the `amplpy` package is itself very professional, as of this writing, AMPL digital rights management is quite
primitive. It is far below the level of sophistication of what `gurobipy` allows you to do with a `gurobi.lic` file.
Until AMPL upgrades their digital rights management, you will likely end up using `amplpy` exclusively to write Python 
code that has serious portability problems due to the limitations of AMPL's licensing technology. 
Such problems will likely  render your `amplpy`based work incompatible with modern cloud based architectures. 

Feel free to prove me wrong, however. I am only relaying my experience fruitlessly trying to run AMPL code in a world 
that is increasingly dominated by Python, Docker, and Kubernetes. If the fault is indeed mine, then I'd love to see a 
public demonstration proving as much.

---

These examples use `PanDatFactory` to connect `amplpy` seamlessly with `pandas`. 

Note that these examples validate input data integrity with both AMPL and `ticdat` code. `ticdat` is used to make data 
integrity problems apparent to another Python programmer. AMPL is used to simply double check that the `ticdat` 
checks are comprehensive.  
 * diet - standard diet example. Easiest example.
 * netflow - standard multi-commodity network flow problem. Second easiest example.
 * fantop - fantasy football example. See [here](https://www.linkedin.com/pulse/fantasy-footballers-nerds-too-peter-cacioppi/) for more information. This is a good example of using `pandas` for pre and post solve data munging.
 * metrorail - optimize the number of times you visit the fare kiosk when riding the metro. See [here](https://www.linkedin.com/pulse/miami-metrorail-meets-python-peter-cacioppi/) for more information. This is a good example of constructing a comprehensive solution from a series of sub-problems.
 * workforce - Demonstrates lexicographical optimization for a workforce scheduling problem.
 * simplest_examples - examples shrunk down by removing the data integrity checking functionality. 
