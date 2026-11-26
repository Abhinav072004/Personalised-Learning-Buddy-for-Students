"""Authoring helper: writes the knowledge-base seed files into data/seed/.

The seed files (CSV / JSON) are the source of truth that the app loads at start-up
and that admins edit. This script only exists so the hand-authored content lives
in one reviewable place; re-running it overwrites courses/skills/modules/
resources/questions/goals/rules/programmes/minors (NOT students.json).

    python scripts/build_kb.py
"""
import csv
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "seed"
OUT.mkdir(parents=True, exist_ok=True)

VERIFIED = "2026-11"
INST_SRC = ("Institute curriculum (illustrative; modelled on a typical IIT B.Tech "
            "structure - verify against the official academic handbook)")

# ---------------------------------------------------------------------------
# Skills: id, name, category, prereq skills, description
# ---------------------------------------------------------------------------
SKILLS = [
    ("calculus", "Calculus", "math", "", "Limits, derivatives, integrals, multivariable calculus, ODE basics"),
    ("linear_algebra", "Linear algebra", "math", "calculus", "Matrices, determinants, rank, eigenvalues, vector spaces"),
    ("prob_stats", "Probability & statistics", "math", "calculus", "Probability, distributions, estimation, hypothesis testing"),
    ("numerical_methods", "Numerical methods", "math", "calculus,linear_algebra,prog_fund", "Root finding, numerical integration, ODE solvers, linear systems"),
    ("prog_fund", "Programming fundamentals", "cs", "", "Variables, control flow, functions, lists, basic Python/C"),
    ("oop", "Object-oriented programming", "cs", "prog_fund", "Classes, encapsulation, inheritance, polymorphism, design"),
    ("discrete_math", "Discrete mathematics", "cs", "", "Logic, sets, combinatorics, graphs, proofs"),
    ("dsa", "Data structures & algorithms", "cs", "prog_fund,discrete_math", "Arrays, stacks, trees, graphs, sorting, complexity"),
    ("databases", "Databases & SQL", "cs", "dsa", "Relational model, SQL, normalisation, transactions"),
    ("os", "Operating systems", "cs", "dsa", "Processes, threads, scheduling, memory, concurrency"),
    ("networks", "Computer networks", "cs", "os", "TCP/IP, HTTP, DNS, addressing, sockets"),
    ("software_eng", "Software engineering", "cs", "oop", "Version control, testing, design patterns, agile"),
    ("web_dev", "Web development", "cs", "prog_fund,databases", "HTML/CSS/JS, HTTP APIs, REST, deployment"),
    ("data_analysis", "Data analysis with Python", "data", "prog_fund,prob_stats", "pandas, cleaning, aggregation, visualisation"),
    ("ml", "Machine learning", "data", "linear_algebra,prob_stats,data_analysis", "Supervised learning, regression, classification, validation"),
    ("thermodynamics", "Thermodynamics", "engg", "calculus", "Laws of thermodynamics, cycles, properties, phase equilibria"),
    ("fluid_mechanics", "Fluid mechanics", "engg", "calculus", "Fluid statics, Bernoulli, pipe flow, dimensionless numbers"),
    ("heat_transfer", "Heat transfer", "engg", "thermodynamics,fluid_mechanics", "Conduction, convection, radiation, heat exchangers"),
    ("mass_transfer", "Mass transfer", "engg", "heat_transfer", "Diffusion, distillation, absorption, extraction"),
    ("reaction_eng", "Chemical reaction engineering", "engg", "thermodynamics", "Kinetics, ideal reactors, conversion, design"),
    ("process_control", "Process dynamics & control", "engg", "calculus", "Laplace transforms, transfer functions, PID control, stability"),
    ("solid_mechanics", "Solid mechanics", "engg", "calculus", "Stress, strain, bending, torsion, deflection"),
    ("manufacturing", "Manufacturing processes", "engg", "", "Casting, forming, machining, welding, metrology"),
    ("machine_design", "Machine design", "engg", "solid_mechanics", "Failure theories, fatigue, shafts, joints, bearings"),
    ("cad_modelling", "Engineering drawing & CAD", "engg", "", "Projections, 3D modelling, GD&T, drafting"),
    ("material_energy_balance", "Material & energy balances", "engg", "calculus", "Process flow, mass and energy balances with and without reaction"),
    ("research_methods", "Research methods", "research", "prob_stats", "Literature review, hypotheses, experimental design, reading papers"),
    ("tech_writing", "Technical writing & communication", "research", "", "Reports, papers, essays, presentations, citation"),
    ("polity_governance", "Indian polity & governance", "humanities", "", "Constitution, institutions, rights, governance"),
    ("economics", "Economics", "humanities", "", "Micro and macro economics, Indian economy"),
    ("history_society", "Indian history & society", "humanities", "", "Modern Indian history, freedom movement, society"),
    ("ethics_aptitude", "Ethics, integrity & aptitude", "humanities", "", "Ethics in public life, probity, emotional intelligence"),
    ("entrepreneurship", "Entrepreneurship", "business", "economics", "Opportunity discovery, MVPs, business models, fundraising"),
    ("product_mgmt", "Product management", "business", "", "User research, prioritisation, metrics, experimentation"),
    ("business_fundamentals", "Finance & accounting basics", "business", "", "Financial statements, margins, NPV, unit economics"),
    ("aptitude", "Quantitative aptitude & reasoning", "general", "", "Arithmetic, percentages, ratios, time-work, logical reasoning"),
]

# ---------------------------------------------------------------------------
# Courses
# code, title, dept, credits, offered, type, mode, programme, semester,
# weekly self-study hours, syllabus, objectives
# ---------------------------------------------------------------------------
FY = "CHE,ME"
COURSES = [
    # first year (common)
    ("MA101", "Mathematics I: Calculus", "MA", 4, "odd", "core", "offline", FY, 1, 4,
     "Limits, continuity, differentiation, integration, series, multivariable calculus", "Apply single and multivariable calculus to engineering problems"),
    ("PH101", "Physics I: Mechanics & Waves", "PH", 4, "odd", "core", "offline", FY, 1, 4,
     "Newtonian mechanics, oscillations, waves", "Model physical systems with Newtonian mechanics"),
    ("CS101", "Introduction to Programming", "CSE", 4, "odd", "core", "offline", FY, 1, 4,
     "Python basics, control flow, functions, lists, dictionaries, files, debugging", "Write, test and debug small programs"),
    ("HS101", "English Communication", "HSS", 3, "odd", "core", "offline", FY, 1, 2,
     "Technical writing, presentations, listening, reading", "Communicate clearly in writing and speech"),
    ("MA102", "Mathematics II: Linear Algebra & ODEs", "MA", 4, "even", "core", "offline", FY, 2, 4,
     "Matrices, rank, eigenvalues, vector spaces, first and second order ODEs", "Solve linear systems and ODEs"),
    ("CY101", "Chemistry", "CY", 4, "even", "core", "offline", FY, 2, 3,
     "Atomic structure, chemical thermodynamics, kinetics, electrochemistry", "Apply chemical principles to engineering"),
    ("ME102", "Engineering Graphics", "ME", 3, "even", "core", "offline", FY, 2, 2,
     "Orthographic and isometric projections, sections, introduction to CAD", "Read and produce engineering drawings"),
    ("MA201", "Mathematics III: Probability, Statistics & Numerical Methods", "MA", 4, "odd", "core", "offline", FY, 3, 4,
     "Probability, random variables, distributions, estimation, root finding, numerical integration", "Apply statistics and numerical methods"),
    # Chemical engineering core
    ("CH201", "Material and Energy Balances", "CHE", 4, "odd", "core", "offline", "CHE", 3, 4,
     "Process variables, balances on reactive and non-reactive systems, energy balances", "Formulate and solve process balances"),
    ("CH202", "Fluid Mechanics for Chemical Engineers", "CHE", 4, "odd", "core", "offline", "CHE", 3, 4,
     "Fluid statics, Bernoulli, pipe flow, pumps, flow measurement", "Design simple fluid flow systems"),
    ("CH203", "Chemical Engineering Thermodynamics", "CHE", 4, "even", "core", "offline", "CHE", 4, 4,
     "Laws of thermodynamics, PVT behaviour, phase and reaction equilibria", "Analyse phase and chemical equilibria"),
    ("CH204", "Heat Transfer", "CHE", 4, "even", "core", "offline", "CHE", 4, 4,
     "Conduction, convection, radiation, heat exchangers, evaporators", "Design heat exchange equipment"),
    ("CH301", "Mass Transfer", "CHE", 4, "odd", "core", "offline", "CHE", 5, 4,
     "Diffusion, interphase transfer, distillation, absorption, extraction", "Design separation units"),
    ("CH302", "Chemical Reaction Engineering", "CHE", 4, "odd", "core", "offline", "CHE", 5, 4,
     "Kinetics, batch/CSTR/PFR design, multiple reactions, non-isothermal reactors", "Size and select ideal reactors"),
    ("CH303", "Process Dynamics and Control", "CHE", 4, "even", "core", "offline", "CHE", 6, 4,
     "Laplace transforms, transfer functions, PID, stability, tuning", "Design feedback control loops"),
    ("CH304", "Process Design and Economics", "CHE", 4, "even", "core", "offline", "CHE", 6, 4,
     "Flowsheet synthesis, equipment sizing, costing, profitability", "Produce an economically evaluated process design"),
    ("CH401", "Process Modelling and Simulation", "CHE", 3, "odd", "dept_elective", "offline", "CHE", 0, 3,
     "Model formulation, numerical solution of process models, simulation in Python", "Build and solve process models numerically"),
    ("CH403", "Data-driven Process Analytics", "CHE", 3, "even", "dept_elective", "offline", "CHE", 0, 3,
     "Process data, statistical process control, regression, intro ML for plants", "Analyse plant data for decisions"),
    # Mechanical engineering core
    ("ME201", "Engineering Thermodynamics", "ME", 4, "odd", "core", "offline", "ME", 3, 4,
     "Properties, laws of thermodynamics, cycles, entropy", "Analyse thermodynamic cycles"),
    ("ME202", "Solid Mechanics", "ME", 4, "odd", "core", "offline", "ME", 3, 4,
     "Stress, strain, bending, torsion, deflection of beams", "Compute stresses and deflections"),
    ("ME203", "Fluid Mechanics", "ME", 4, "even", "core", "offline", "ME", 4, 4,
     "Fluid statics, kinematics, Bernoulli, viscous flow, boundary layers", "Analyse internal and external flows"),
    ("ME204", "Kinematics and Dynamics of Machines", "ME", 4, "even", "core", "offline", "ME", 4, 4,
     "Mechanisms, gears, cams, balancing, vibrations", "Analyse mechanisms and machine dynamics"),
    ("ME301", "Heat and Mass Transfer", "ME", 4, "odd", "core", "offline", "ME", 5, 4,
     "Conduction, convection, radiation, heat exchangers, diffusion", "Design thermal systems"),
    ("ME302", "Manufacturing Processes", "ME", 4, "odd", "core", "offline", "ME", 5, 4,
     "Casting, forming, machining, welding, metrology", "Select manufacturing processes"),
    ("ME303", "Design of Machine Elements", "ME", 4, "even", "core", "offline", "ME", 6, 4,
     "Failure theories, fatigue, shafts, keys, bearings, gears", "Design safe machine elements"),
    ("ME304", "Control Systems", "ME", 4, "even", "core", "offline", "ME", 6, 4,
     "Laplace, transfer functions, time response, PID, stability, root locus", "Design feedback controllers"),
    ("ME401", "CAD/CAM", "ME", 3, "odd", "dept_elective", "offline", "ME", 0, 3,
     "Parametric modelling, assemblies, GD&T, CNC programming", "Model and manufacture parts digitally"),
    ("ME402", "Computational Fluid Dynamics", "ME", 3, "even", "dept_elective", "offline", "ME", 0, 4,
     "Discretisation, finite volume, solvers, turbulence models", "Simulate flows numerically"),
    # shared project
    ("BT491", "B.Tech Project I", "ALL", 4, "odd", "core", "offline", FY, 7, 6,
     "Supervised project: literature review, problem definition, experiments/design, report", "Carry out and report an independent project"),
    # CSE (minor / open elective)
    ("CS102", "Data Structures", "CSE", 4, "both", "minor", "offline", "", 0, 4,
     "Arrays, linked lists, stacks, queues, trees, heaps, hashing, complexity", "Choose and implement appropriate data structures"),
    ("CS201", "Discrete Mathematics", "CSE", 4, "odd", "minor", "offline", "", 0, 4,
     "Logic, proofs, sets, relations, combinatorics, graphs", "Reason formally about discrete structures"),
    ("CS202", "Object-Oriented Programming", "CSE", 4, "odd", "minor", "offline", "", 0, 4,
     "Classes, inheritance, polymorphism, interfaces, design patterns in Java/Python", "Design modular object-oriented programs"),
    ("CS203", "Design and Analysis of Algorithms", "CSE", 4, "even", "minor", "offline", "", 0, 5,
     "Divide and conquer, greedy, dynamic programming, graph algorithms, NP-completeness", "Design and analyse efficient algorithms"),
    ("CS204", "Database Systems", "CSE", 4, "odd", "minor", "offline", "", 0, 4,
     "Relational model, SQL, ER design, normalisation, indexing, transactions", "Design and query relational databases"),
    ("CS301", "Operating Systems", "CSE", 4, "odd", "minor", "offline", "", 0, 4,
     "Processes, threads, scheduling, synchronisation, memory management, file systems", "Explain and use OS abstractions"),
    ("CS302", "Computer Networks", "CSE", 4, "even", "minor", "offline", "", 0, 4,
     "Layering, TCP/IP, routing, transport, HTTP, DNS, sockets", "Explain and program networked systems"),
    ("CS303", "Software Engineering", "CSE", 4, "even", "minor", "offline", "", 0, 4,
     "Requirements, design, version control, testing, CI, agile team project", "Build software in a team with good practice"),
    ("CS304", "Machine Learning", "CSE", 4, "odd", "minor", "offline", "", 0, 5,
     "Regression, classification, regularisation, trees, SVMs, neural networks, evaluation", "Train and evaluate ML models"),
    ("CS305", "Web Application Development", "CSE", 3, "even", "open_elective", "offline", "", 0, 4,
     "HTML/CSS/JS, HTTP, REST APIs, backend frameworks, databases, deployment", "Build and deploy a web application"),
    ("DS201", "Data Analysis with Python", "CSE", 3, "both", "open_elective", "offline", "", 0, 3,
     "NumPy, pandas, cleaning, aggregation, visualisation, exploratory analysis", "Analyse real datasets end to end"),
    # Humanities & social sciences
    ("HS201", "Introduction to Economics", "HSS", 3, "odd", "open_elective", "offline", "", 0, 3,
     "Demand and supply, market structures, national income, inflation, monetary policy, Indian economy", "Use economic reasoning"),
    ("HS202", "Indian Polity and Constitution", "HSS", 3, "even", "open_elective", "offline", "", 0, 3,
     "Constitution, fundamental rights, DPSP, Parliament, judiciary, federalism, local government", "Explain India's constitutional framework"),
    ("HS203", "Modern Indian History and Society", "HSS", 3, "odd", "open_elective", "offline", "", 0, 3,
     "Colonial rule, freedom movement, social reform, post-independence India", "Analyse modern Indian history"),
    ("HS204", "Ethics in Public Life", "HSS", 3, "even", "open_elective", "offline", "", 0, 2,
     "Ethical theories, integrity, probity, case studies in governance", "Reason through ethical dilemmas"),
    ("HS205", "Technical and Research Writing", "HSS", 3, "both", "open_elective", "offline", "", 0, 2,
     "Structure of papers and reports, IMRaD, citation, editing, presentations", "Write clear technical documents"),
    # Management / entrepreneurship
    ("MS201", "Entrepreneurship and New Ventures", "MGMT", 3, "odd", "open_elective", "offline", "", 0, 3,
     "Opportunity discovery, customer development, MVP, business models, funding", "Develop and test a venture idea"),
    ("MS202", "Product Management Fundamentals", "MGMT", 3, "even", "open_elective", "offline", "", 0, 3,
     "User research, roadmaps, prioritisation, metrics, experimentation", "Plan and measure a product"),
    ("MS203", "Financial Accounting for Engineers", "MGMT", 3, "odd", "open_elective", "offline", "", 0, 2,
     "Financial statements, ratios, costing, time value of money, NPV", "Read financial statements and evaluate projects"),
    # Research
    ("RM301", "Research Methodology", "ALL", 3, "odd", "open_elective", "offline", "", 0, 3,
     "Reading papers, literature review, hypotheses, experimental design, statistics for research", "Plan a research study"),
    # Online, credit-eligible (NPTEL / SWAYAM)
    ("NP101", "NPTEL: Programming, Data Structures and Algorithms using Python", "ONLINE", 3, "both", "online", "online", "", 0, 5,
     "Python, searching, sorting, lists, dictionaries, recursion, basic graph algorithms", "Program and analyse basic algorithms"),
    ("NP102", "NPTEL: Database Management System", "ONLINE", 3, "both", "online", "online", "", 0, 4,
     "Relational model, SQL, design, normalisation, storage, transactions", "Design and query databases"),
    ("NP103", "NPTEL: Introduction to Machine Learning", "ONLINE", 3, "both", "online", "online", "", 0, 5,
     "Regression, classification, model selection, neural networks, clustering", "Apply ML algorithms"),
]
ONLINE_SRC = {
    "NP101": "NPTEL course 106106145 (IIT Madras), https://nptel.ac.in/courses/106106145",
    "NP102": "NPTEL course 106105175 (IIT Kharagpur), https://nptel.ac.in/courses/106105175",
    "NP103": "NPTEL catalogue - Introduction to Machine Learning, https://nptel.ac.in/courses",
}

PREREQS = [
    ("MA102", "MA101"), ("MA201", "MA101"),
    ("CS102", "CS101"), ("CS202", "CS101"), ("CS203", "CS102"), ("CS203", "CS201"),
    ("CS204", "CS102"), ("CS301", "CS102"), ("CS302", "CS102"), ("CS303", "CS202"),
    ("CS304", "MA102"), ("CS304", "MA201"), ("CS304", "CS101"), ("CS305", "CS101"),
    ("DS201", "CS101"), ("NP102", "CS101"), ("NP103", "MA201"), ("NP103", "CS101"),
    ("CH202", "MA101"), ("CH203", "CH201"), ("CH204", "CH202"), ("CH301", "CH204"),
    ("CH302", "CH203"), ("CH303", "MA102"), ("CH304", "CH301"), ("CH304", "CH302"),
    ("CH401", "CS101"), ("CH401", "MA201"), ("CH403", "MA201"), ("CH403", "CS101"),
    ("ME203", "MA101"), ("ME204", "ME202"), ("ME301", "ME201"), ("ME301", "ME203"),
    ("ME303", "ME202"), ("ME304", "MA102"), ("ME401", "ME102"), ("ME402", "ME203"), ("ME402", "MA201"),
    ("RM301", "MA201"),
]

COURSE_SKILLS = {
    "MA101": [("calculus", .7)],
    "MA102": [("linear_algebra", .65), ("calculus", .8)],
    "MA201": [("prob_stats", .6), ("numerical_methods", .5)],
    "PH101": [("solid_mechanics", .2)],
    "CS101": [("prog_fund", .6)],
    "HS101": [("tech_writing", .4)],
    "CY101": [("thermodynamics", .25), ("reaction_eng", .2)],
    "ME102": [("cad_modelling", .5)],
    "CH201": [("material_energy_balance", .8)],
    "CH202": [("fluid_mechanics", .7)],
    "CH203": [("thermodynamics", .8)],
    "CH204": [("heat_transfer", .75)],
    "CH301": [("mass_transfer", .75)],
    "CH302": [("reaction_eng", .8)],
    "CH303": [("process_control", .75)],
    "CH304": [("material_energy_balance", .9), ("business_fundamentals", .3)],
    "CH401": [("numerical_methods", .75), ("prog_fund", .65)],
    "CH403": [("data_analysis", .6), ("ml", .35), ("prob_stats", .65)],
    "ME201": [("thermodynamics", .8)],
    "ME202": [("solid_mechanics", .8)],
    "ME203": [("fluid_mechanics", .8)],
    "ME204": [("machine_design", .4)],
    "ME301": [("heat_transfer", .8), ("mass_transfer", .35)],
    "ME302": [("manufacturing", .8)],
    "ME303": [("machine_design", .8)],
    "ME304": [("process_control", .75)],
    "ME401": [("cad_modelling", .85), ("manufacturing", .55)],
    "ME402": [("numerical_methods", .75), ("fluid_mechanics", .9)],
    "BT491": [("research_methods", .55), ("tech_writing", .55)],
    "CS102": [("dsa", .55), ("prog_fund", .8)],
    "CS201": [("discrete_math", .8)],
    "CS202": [("oop", .8), ("prog_fund", .8)],
    "CS203": [("dsa", .85)],
    "CS204": [("databases", .8)],
    "CS301": [("os", .8)],
    "CS302": [("networks", .8)],
    "CS303": [("software_eng", .8), ("oop", .85)],
    "CS304": [("ml", .7), ("data_analysis", .55)],
    "CS305": [("web_dev", .8)],
    "DS201": [("data_analysis", .75), ("prob_stats", .65)],
    "HS201": [("economics", .7)],
    "HS202": [("polity_governance", .7)],
    "HS203": [("history_society", .7)],
    "HS204": [("ethics_aptitude", .7)],
    "HS205": [("tech_writing", .8), ("research_methods", .3)],
    "MS201": [("entrepreneurship", .7), ("business_fundamentals", .4)],
    "MS202": [("product_mgmt", .7)],
    "MS203": [("business_fundamentals", .7)],
    "RM301": [("research_methods", .75), ("prob_stats", .65)],
    "NP101": [("prog_fund", .75), ("dsa", .6)],
    "NP102": [("databases", .7)],
    "NP103": [("ml", .65)],
}

# ---------------------------------------------------------------------------
# Open learning resources (real, openly available). id, title, provider, url,
# skills, format, level, hours, licence, credit_eligible
# ---------------------------------------------------------------------------
OCW = "https://ocw.mit.edu/courses/"
RESOURCES = [
    ("R_MIT1801", "MIT 18.01SC Single Variable Calculus", "MIT OCW", OCW + "18-01sc-single-variable-calculus-fall-2010/", "calculus", "course", 1, 30, "CC BY-NC-SA", False),
    ("R_KA_CALC", "Khan Academy: Calculus 1", "Khan Academy", "https://www.khanacademy.org/math/calculus-1", "calculus", "video", 1, 15, "CC BY-NC-SA", False),
    ("R_MIT1806", "MIT 18.06 Linear Algebra (Gilbert Strang)", "MIT OCW", OCW + "18-06-linear-algebra-spring-2010/", "linear_algebra", "video", 2, 35, "CC BY-NC-SA", False),
    ("R_3B1B_LA", "Essence of Linear Algebra (video series)", "3Blue1Brown", "https://www.3blue1brown.com/topics/linear-algebra", "linear_algebra", "video", 1, 4, "Free to view", False),
    ("R_MIT1805", "MIT 18.05 Introduction to Probability and Statistics", "MIT OCW", OCW + "18-05-introduction-to-probability-and-statistics-spring-2014/", "prob_stats,research_methods", "course", 2, 30, "CC BY-NC-SA", False),
    ("R_KA_STATS", "Khan Academy: Statistics and Probability", "Khan Academy", "https://www.khanacademy.org/math/statistics-probability", "prob_stats,data_analysis", "video", 1, 20, "CC BY-NC-SA", False),
    ("R_MIT10_34", "MIT 10.34 Numerical Methods Applied to Chemical Engineering", "MIT OCW", OCW + "10-34-numerical-methods-applied-to-chemical-engineering-fall-2015/", "numerical_methods", "course", 3, 30, "CC BY-NC-SA", False),
    ("R_MIT6_0001", "MIT 6.0001 Introduction to Computer Science and Programming in Python", "MIT OCW", OCW + "6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/", "prog_fund", "video", 1, 25, "CC BY-NC-SA", False),
    ("R_CS50", "CS50x: Introduction to Computer Science", "Harvard (CS50)", "https://cs50.harvard.edu/x/", "prog_fund,dsa,web_dev", "video", 1, 40, "CC BY-NC-SA", False),
    ("R_NPTEL_PDSA", "NPTEL: Programming, Data Structures and Algorithms using Python", "NPTEL", "https://nptel.ac.in/courses/106106145", "prog_fund,dsa", "course", 2, 40, "CC BY-SA (NPTEL)", True),
    ("R_MIT6_006", "MIT 6.006 Introduction to Algorithms", "MIT OCW", OCW + "6-006-introduction-to-algorithms-spring-2020/", "dsa", "video", 2, 40, "CC BY-NC-SA", False),
    ("R_NPTEL_DSA", "NPTEL: Data Structures and Algorithms (IIT Delhi)", "NPTEL", "https://nptel.ac.in/courses/106102064", "dsa", "video", 2, 30, "CC BY-SA (NPTEL)", False),
    ("R_PRACTICE_DSA", "Coding-practice platform problem sets (arrays, trees, graphs, DP)", "Coding practice", "https://leetcode.com/problemset/", "dsa", "practice", 2, 30, "Free tier", False),
    ("R_MIT6_042", "MIT 6.042J Mathematics for Computer Science", "MIT OCW", OCW + "6-042j-mathematics-for-computer-science-spring-2015/", "discrete_math", "course", 2, 35, "CC BY-NC-SA", False),
    ("R_MIT6_005", "MIT 6.005 Software Construction", "MIT OCW", OCW + "6-005-software-construction-spring-2016/", "oop,software_eng", "text", 2, 30, "CC BY-NC-SA", False),
    ("R_NPTEL_DBMS", "NPTEL: Database Management System (IIT Kharagpur)", "NPTEL", "https://nptel.ac.in/courses/106105175", "databases", "course", 2, 30, "CC BY-SA (NPTEL)", True),
    ("R_SQLBOLT", "SQLBolt interactive SQL lessons", "SQLBolt", "https://sqlbolt.com/", "databases", "practice", 1, 5, "Free", False),
    ("R_KAGGLE_SQL", "Kaggle Learn: Intro to SQL", "Kaggle Learn", "https://www.kaggle.com/learn/intro-to-sql", "databases,data_analysis", "practice", 1, 4, "Free", False),
    ("R_OSTEP", "Operating Systems: Three Easy Pieces (free textbook)", "OSTEP", "https://pages.cs.wisc.edu/~remzi/OSTEP/", "os", "text", 2, 30, "Free online", False),
    ("R_MIT6_828", "MIT 6.828 Operating System Engineering", "MIT OCW", OCW + "6-828-operating-system-engineering-fall-2012/", "os", "course", 3, 40, "CC BY-NC-SA", False),
    ("R_NPTEL_CN", "NPTEL: Computer Networks and Internet Protocol", "NPTEL", "https://nptel.ac.in/courses", "networks", "video", 2, 30, "CC BY-SA (NPTEL)", True),
    ("R_MISSING", "The Missing Semester of Your CS Education (shell, git, tools)", "MIT CSAIL", "https://missing.csail.mit.edu/", "software_eng", "video", 1, 11, "CC BY-NC-SA", False),
    ("R_ODIN", "The Odin Project: Full-stack web development", "The Odin Project", "https://www.theodinproject.com/", "web_dev", "practice", 1, 60, "Free (CC BY-NC-SA content)", False),
    ("R_MDN", "MDN Web Docs: Learn web development", "MDN", "https://developer.mozilla.org/en-US/docs/Learn", "web_dev", "text", 1, 20, "CC BY-SA", False),
    ("R_KAGGLE_PANDAS", "Kaggle Learn: Pandas", "Kaggle Learn", "https://www.kaggle.com/learn/pandas", "data_analysis", "practice", 1, 4, "Free", False),
    ("R_PYDSH", "Python Data Science Handbook (Jake VanderPlas)", "Open book", "https://jakevdp.github.io/PythonDataScienceHandbook/", "data_analysis,ml", "text", 2, 25, "CC BY-NC-ND (text), MIT (code)", False),
    ("R_MIT6_036", "MIT 6.036 Introduction to Machine Learning", "MIT OCW", OCW + "6-036-introduction-to-machine-learning-fall-2020/", "ml", "course", 2, 40, "CC BY-NC-SA", False),
    ("R_GOOGLE_MLCC", "Google Machine Learning Crash Course", "Google", "https://developers.google.com/machine-learning/crash-course", "ml", "video", 1, 15, "CC BY 4.0", False),
    ("R_NPTEL_ML", "NPTEL: Introduction to Machine Learning", "NPTEL", "https://nptel.ac.in/courses", "ml", "course", 2, 40, "CC BY-SA (NPTEL)", True),
    ("R_MIT10_40", "MIT 10.40 Chemical Engineering Thermodynamics", "MIT OCW", OCW + "10-40-chemical-engineering-thermodynamics-fall-2003/", "thermodynamics", "text", 2, 30, "CC BY-NC-SA", False),
    ("R_NPTEL_THERMO", "NPTEL: Basic Thermodynamics / Applied Thermodynamics (Mechanical)", "NPTEL", "https://nptel.ac.in/courses", "thermodynamics", "video", 1, 25, "CC BY-SA (NPTEL)", True),
    ("R_MIT2_25", "MIT 2.25 Advanced Fluid Mechanics", "MIT OCW", OCW + "2-25-advanced-fluid-mechanics-fall-2013/", "fluid_mechanics", "course", 3, 35, "CC BY-NC-SA", False),
    ("R_NPTEL_FM", "NPTEL: Fluid Mechanics", "NPTEL", "https://nptel.ac.in/courses", "fluid_mechanics", "video", 1, 25, "CC BY-SA (NPTEL)", True),
    ("R_LIENHARD", "A Heat Transfer Textbook (Lienhard & Lienhard, free)", "Open book", "https://ahtt.mit.edu/", "heat_transfer,mass_transfer", "text", 2, 30, "Free (author-provided)", False),
    ("R_NPTEL_HMT", "NPTEL: Heat and Mass Transfer", "NPTEL", "https://nptel.ac.in/courses", "heat_transfer,mass_transfer", "video", 1, 25, "CC BY-SA (NPTEL)", True),
    ("R_MIT10_37", "MIT 10.37 Chemical and Biological Reaction Engineering", "MIT OCW", OCW + "10-37-chemical-and-biological-reaction-engineering-spring-2007/", "reaction_eng", "course", 2, 30, "CC BY-NC-SA", False),
    ("R_LEARNCHEME", "LearnChemE screencasts and interactive simulations", "University of Colorado Boulder", "https://learncheme.com/", "material_energy_balance,reaction_eng,mass_transfer,thermodynamics", "video", 1, 15, "CC BY (most content)", False),
    ("R_MIT10_450", "MIT 10.450 Process Dynamics, Operations, and Control", "MIT OCW", OCW + "10-450-process-dynamics-operations-and-control-spring-2006/", "process_control", "course", 2, 25, "CC BY-NC-SA", False),
    ("R_MIT2_14", "MIT 2.14 Analysis and Design of Feedback Control Systems", "MIT OCW", OCW + "2-14-analysis-and-design-of-feedback-control-systems-spring-2014/", "process_control", "course", 3, 30, "CC BY-NC-SA", False),
    ("R_MIT2_001", "MIT 2.001 Mechanics and Materials I", "MIT OCW", OCW + "2-001-mechanics-materials-i-fall-2006/", "solid_mechanics,machine_design", "course", 2, 30, "CC BY-NC-SA", False),
    ("R_MIT2_008", "MIT 2.008 Design and Manufacturing II", "MIT OCW", OCW + "2-008-design-and-manufacturing-ii-spring-2004/", "manufacturing", "course", 2, 25, "CC BY-NC-SA", False),
    ("R_NPTEL_MFG", "NPTEL: Manufacturing Processes", "NPTEL", "https://nptel.ac.in/courses", "manufacturing", "video", 1, 25, "CC BY-SA (NPTEL)", True),
    ("R_NPTEL_DME", "NPTEL: Design of Machine Elements", "NPTEL", "https://nptel.ac.in/courses", "machine_design", "video", 2, 25, "CC BY-SA (NPTEL)", True),
    ("R_FREECAD", "FreeCAD documentation and tutorials", "FreeCAD", "https://wiki.freecad.org/Tutorials", "cad_modelling", "practice", 1, 10, "CC BY 3.0", False),
    ("R_MIT10_10", "MIT 10.10 Introduction to Chemical Engineering", "MIT OCW", OCW + "10-10-introduction-to-chemical-engineering-fall-2020/", "material_energy_balance", "course", 1, 20, "CC BY-NC-SA", False),
    ("R_KESHAV", "How to Read a Paper (S. Keshav)", "ACM SIGCOMM CCR", "http://ccr.sigcomm.org/online/files/p83-keshavA.pdf", "research_methods", "text", 1, 1, "Free", False),
    ("R_PURDUE_OWL", "Purdue Online Writing Lab (OWL)", "Purdue OWL", "https://owl.purdue.edu/owl/purdue_owl.html", "tech_writing", "text", 1, 8, "Free", False),
    ("R_MIT21W", "MIT 21W.035 Science Writing and New Media", "MIT OCW", OCW + "21w-035-science-writing-and-new-media-fall-2015/", "tech_writing", "text", 2, 15, "CC BY-NC-SA", False),
    ("R_NCERT_POL", "NCERT Class XI: Indian Constitution at Work", "NCERT", "https://ncert.nic.in/textbook.php", "polity_governance", "text", 1, 20, "Free (Govt. of India)", False),
    ("R_UPSC_SYL", "UPSC Civil Services Examination notice & syllabus", "UPSC", "https://upsc.gov.in/examinations/active-exams", "polity_governance,history_society,economics,ethics_aptitude", "text", 1, 2, "Public", False),
    ("R_NCERT_ECO", "NCERT Class XI/XII: Indian Economic Development, Macroeconomics", "NCERT", "https://ncert.nic.in/textbook.php", "economics", "text", 1, 25, "Free (Govt. of India)", False),
    ("R_MIT14_01", "MIT 14.01 Principles of Microeconomics", "MIT OCW", OCW + "14-01-principles-of-microeconomics-fall-2018/", "economics", "video", 2, 30, "CC BY-NC-SA", False),
    ("R_NCERT_HIS", "NCERT Class XII: Themes in Indian History III; Spectrum-style revision notes", "NCERT", "https://ncert.nic.in/textbook.php", "history_society", "text", 1, 25, "Free (Govt. of India)", False),
    ("R_NPTEL_ETHICS", "NPTEL humanities: Ethics (philosophy) lectures", "NPTEL", "https://nptel.ac.in/courses", "ethics_aptitude", "video", 1, 15, "CC BY-SA (NPTEL)", False),
    ("R_YCSS", "Y Combinator Startup School", "Y Combinator", "https://www.startupschool.org/", "entrepreneurship,product_mgmt", "video", 1, 20, "Free", False),
    ("R_MIT15_390", "MIT 15.390 New Enterprises", "MIT OCW", OCW + "15-390-new-enterprises-spring-2013/", "entrepreneurship", "course", 2, 25, "CC BY-NC-SA", False),
    ("R_MIT15_401", "MIT 15.401 Finance Theory I", "MIT OCW", OCW + "15-401-finance-theory-i-fall-2008/", "business_fundamentals", "video", 2, 25, "CC BY-NC-SA", False),
    ("R_KA_FIN", "Khan Academy: Accounting and financial statements", "Khan Academy", "https://www.khanacademy.org/economics-finance-domain/core-finance", "business_fundamentals", "video", 1, 8, "CC BY-NC-SA", False),
    ("R_PM_MIT", "MIT 15.783J Product Design and Development", "MIT OCW", OCW + "15-783j-product-design-and-development-spring-2006/", "product_mgmt", "course", 2, 20, "CC BY-NC-SA", False),
    ("R_APT_PRACTICE", "Quantitative aptitude practice sets (percentages, ratios, time-work)", "Institute T&P cell (illustrative)", "local://tnp/aptitude-sets", "aptitude", "practice", 1, 15, "Institute internal", False),
    ("R_KA_ARITH", "Khan Academy: Arithmetic and pre-algebra", "Khan Academy", "https://www.khanacademy.org/math/arithmetic", "aptitude", "video", 1, 10, "CC BY-NC-SA", False),
]

# ---------------------------------------------------------------------------
# Modules / lessons: per skill, an ordered list of (title, level, kind, hours)
# ---------------------------------------------------------------------------
L, B, P = "lesson", "lab", "project"
MODULES = {
    "calculus": [("Limits and continuity", 1, L, 2), ("Derivatives and applications", 1, L, 3), ("Integration techniques", 2, L, 3), ("Multivariable calculus and partial derivatives", 2, L, 3), ("Problem set: optimisation and area problems", 2, B, 2)],
    "linear_algebra": [("Matrices and Gaussian elimination", 1, L, 2), ("Determinants and inverses", 1, L, 2), ("Vector spaces, rank and null space", 2, L, 3), ("Eigenvalues and eigenvectors", 2, L, 3), ("Lab: least squares and PCA in NumPy", 3, B, 3)],
    "prob_stats": [("Probability rules and conditional probability", 1, L, 2), ("Random variables and distributions", 2, L, 3), ("Descriptive statistics", 1, L, 2), ("Estimation and confidence intervals", 2, L, 3), ("Hypothesis testing", 3, L, 3), ("Problem set: statistics on real data", 2, B, 3)],
    "numerical_methods": [("Root finding: bisection and Newton-Raphson", 1, L, 2), ("Solving linear systems: Gauss elimination, Gauss-Seidel", 2, L, 3), ("Numerical integration: trapezoidal and Simpson", 1, L, 2), ("ODE solvers: Euler and Runge-Kutta", 2, L, 3), ("Lab: solve a process/engineering model in Python", 3, B, 4)],
    "prog_fund": [("Variables, types and expressions", 1, L, 2), ("Conditionals and loops", 1, L, 2), ("Functions and scope", 1, L, 2), ("Lists, dictionaries and strings", 2, L, 3), ("Files, errors and debugging", 2, L, 2), ("Lab: 15 hands-on coding problems", 2, B, 4)],
    "oop": [("Classes and objects", 1, L, 2), ("Encapsulation and interfaces", 2, L, 2), ("Inheritance and polymorphism", 2, L, 3), ("Composition and design patterns", 3, L, 3), ("Lab: design a library-management system", 3, B, 5)],
    "discrete_math": [("Propositional and predicate logic", 1, L, 2), ("Proof techniques and induction", 2, L, 3), ("Sets, relations and functions", 1, L, 2), ("Counting: permutations and combinations", 2, L, 3), ("Graph theory basics", 2, L, 3), ("Problem set: combinatorics and graphs", 2, B, 3)],
    "dsa": [("Complexity and Big-O", 1, L, 2), ("Arrays, linked lists, stacks and queues", 1, L, 3), ("Hashing", 2, L, 2), ("Trees and heaps", 2, L, 3), ("Sorting and searching", 2, L, 3), ("Graphs: BFS, DFS, shortest paths", 3, L, 4), ("Dynamic programming", 3, L, 4), ("Practice: 50 timed DSA problems", 3, B, 10)],
    "databases": [("Relational model and keys", 1, L, 2), ("SQL: SELECT, WHERE, ORDER BY", 1, L, 2), ("Joins and aggregation (GROUP BY / HAVING)", 2, L, 3), ("ER design and normalisation", 2, L, 3), ("Indexes and transactions (ACID)", 3, L, 3), ("Lab: design and query a college database", 2, B, 4)],
    "os": [("Processes and threads", 1, L, 2), ("CPU scheduling", 2, L, 2), ("Synchronisation and deadlocks", 2, L, 3), ("Memory management and paging", 2, L, 3), ("File systems", 3, L, 2), ("Lab: write a multi-threaded program", 3, B, 4)],
    "networks": [("Layered architecture and TCP/IP", 1, L, 2), ("IP addressing and subnetting", 2, L, 3), ("TCP vs UDP", 2, L, 2), ("HTTP and DNS", 1, L, 2), ("Lab: socket programming", 3, B, 4)],
    "software_eng": [("Version control with git", 1, L, 2), ("Testing: unit and integration tests", 2, L, 3), ("Design principles and patterns", 2, L, 3), ("Agile and code review", 1, L, 2), ("Project: build a tested team project with CI", 3, P, 10)],
    "web_dev": [("HTML and CSS basics", 1, L, 3), ("JavaScript and the DOM", 2, L, 3), ("HTTP and REST APIs", 2, L, 3), ("Backend with a web framework and a database", 2, L, 4), ("Project: build and deploy a full-stack app", 3, P, 12)],
    "data_analysis": [("NumPy arrays", 1, L, 2), ("pandas DataFrames: selection and filtering", 1, L, 3), ("Cleaning and transforming data", 2, L, 3), ("Grouping and aggregation", 2, L, 2), ("Visualisation with matplotlib", 2, L, 2), ("Project: end-to-end exploratory analysis on an open dataset", 3, P, 8)],
    "ml": [("ML problem framing and train/test split", 1, L, 2), ("Linear and logistic regression", 2, L, 3), ("Overfitting, regularisation and cross-validation", 2, L, 3), ("Trees and ensembles", 2, L, 3), ("Evaluation metrics: precision, recall, ROC", 2, L, 2), ("Neural network basics", 3, L, 3), ("Project: Kaggle-style ML pipeline", 3, P, 10)],
    "thermodynamics": [("Systems, properties and the zeroth law", 1, L, 2), ("First law and energy analysis", 1, L, 3), ("Second law, entropy and Carnot efficiency", 2, L, 3), ("Power and refrigeration cycles", 2, L, 3), ("Phase and chemical equilibria", 3, L, 3), ("Problem set: cycle analysis", 2, B, 3)],
    "fluid_mechanics": [("Fluid statics and pressure", 1, L, 2), ("Continuity and Bernoulli equation", 1, L, 3), ("Viscous flow and Reynolds number", 2, L, 2), ("Pipe flow and friction losses", 2, L, 3), ("Pumps and flow measurement", 2, L, 2), ("Problem set: piping network", 3, B, 3)],
    "heat_transfer": [("Conduction and Fourier's law", 1, L, 2), ("Convection and heat transfer coefficients", 2, L, 3), ("Radiation basics", 2, L, 2), ("Heat exchanger design (LMTD, NTU)", 3, L, 3), ("Problem set: exchanger sizing", 3, B, 3)],
    "mass_transfer": [("Diffusion and Fick's law", 1, L, 2), ("Mass transfer coefficients", 2, L, 2), ("Distillation (McCabe-Thiele)", 2, L, 3), ("Absorption and stripping", 2, L, 3), ("Problem set: column design", 3, B, 3)],
    "reaction_eng": [("Rate laws and reaction order", 1, L, 2), ("Arrhenius equation and temperature dependence", 1, L, 2), ("Batch, CSTR and PFR design equations", 2, L, 3), ("Multiple reactions and selectivity", 3, L, 3), ("Problem set: reactor sizing", 3, B, 3)],
    "process_control": [("Laplace transforms", 1, L, 2), ("Transfer functions and first-order systems", 2, L, 3), ("Feedback and PID control", 2, L, 3), ("Stability analysis", 3, L, 3), ("Lab: PID tuning simulation", 3, B, 3)],
    "solid_mechanics": [("Stress and strain", 1, L, 2), ("Axial loading and Hooke's law", 1, L, 2), ("Bending moments and shear force diagrams", 2, L, 3), ("Torsion", 2, L, 2), ("Deflection of beams", 3, L, 3), ("Problem set: beam design", 3, B, 3)],
    "manufacturing": [("Casting processes", 1, L, 2), ("Metal forming", 1, L, 2), ("Machining and tool life", 2, L, 3), ("Welding and joining", 2, L, 2), ("Metrology and quality", 2, L, 2)],
    "machine_design": [("Design process and factor of safety", 1, L, 2), ("Static failure theories", 2, L, 3), ("Fatigue design", 3, L, 3), ("Shafts, keys and couplings", 2, L, 3), ("Project: design a gearbox shaft", 3, P, 6)],
    "cad_modelling": [("Orthographic and isometric projections", 1, L, 2), ("Sketching and constraints in parametric CAD", 1, L, 3), ("Part and assembly modelling", 2, L, 3), ("GD&T basics", 2, L, 2), ("Lab: model an assembly in FreeCAD", 2, B, 4)],
    "material_energy_balance": [("Process variables and units", 1, L, 2), ("Balances on non-reactive systems", 1, L, 3), ("Balances on reactive systems", 2, L, 3), ("Energy balances", 2, L, 3), ("Problem set: recycle and purge", 3, B, 3)],
    "research_methods": [("How to read a research paper", 1, L, 2), ("Literature review and finding gaps", 2, L, 3), ("Hypotheses and experimental design", 2, L, 3), ("Statistics for research results", 2, L, 3), ("Project: write a 2-page research proposal", 3, P, 6)],
    "tech_writing": [("Structure of reports and papers (IMRaD)", 1, L, 2), ("Clear sentences and consistent terminology", 1, L, 2), ("Citations and avoiding plagiarism", 1, L, 1), ("Abstracts, statements of purpose and essays", 2, L, 3), ("Exercise: write and peer-review an essay", 2, B, 3)],
    "polity_governance": [("Making of the Constitution and Preamble", 1, L, 2), ("Fundamental Rights and Duties", 1, L, 3), ("Directive Principles of State Policy", 1, L, 2), ("Parliament, Executive and Judiciary", 2, L, 3), ("Federalism and local government", 2, L, 3), ("Practice: prelims-style polity test", 2, B, 2)],
    "economics": [("Demand, supply and elasticity", 1, L, 2), ("Market structures", 2, L, 2), ("National income and GDP", 1, L, 2), ("Inflation and monetary policy", 2, L, 3), ("Indian economy: planning, reforms, budget", 2, L, 3), ("Practice: economy current-affairs quiz", 2, B, 2)],
    "history_society": [("Advent of European powers and British rule", 1, L, 3), ("Social and religious reform movements", 1, L, 2), ("Indian National Movement 1885-1919", 2, L, 3), ("Gandhian era and independence 1919-1947", 2, L, 3), ("Post-independence consolidation", 2, L, 2), ("Practice: history answer-writing", 2, B, 2)],
    "ethics_aptitude": [("Ethics and human interface", 1, L, 2), ("Attitude and emotional intelligence", 1, L, 2), ("Probity in governance", 2, L, 2), ("Case studies in public administration", 3, B, 3)],
    "entrepreneurship": [("Finding problems worth solving", 1, L, 2), ("Customer discovery interviews", 1, L, 2), ("MVPs and experiments", 2, L, 3), ("Business models and unit economics", 2, L, 3), ("Pitching and fundraising", 2, L, 2), ("Project: 20 customer interviews and an MVP", 3, P, 12)],
    "product_mgmt": [("Product thinking and user needs", 1, L, 2), ("Writing user stories and PRDs", 1, L, 2), ("Prioritisation frameworks (RICE, MoSCoW)", 2, L, 2), ("Metrics and A/B testing", 2, L, 3), ("Case study: product teardown", 2, B, 3)],
    "business_fundamentals": [("Financial statements", 1, L, 2), ("Margins, costing and break-even", 1, L, 2), ("Time value of money and NPV", 2, L, 3), ("Exercise: build a startup financial model", 2, B, 3)],
    "aptitude": [("Percentages, profit and loss", 1, L, 2), ("Ratios and proportions", 1, L, 2), ("Time, speed, distance and work", 2, L, 2), ("Logical reasoning", 2, L, 2), ("Timed aptitude mock test", 2, B, 2)],
}

# ---------------------------------------------------------------------------
# Question bank: skill -> [(difficulty, prompt, options, correct_index, explanation)]
# All MCQ so grading is deterministic and reliable.
# ---------------------------------------------------------------------------
Q = {
    "calculus": [
        (1, "What is d/dx (x^3) evaluated at x = 2?", ["4", "8", "12", "6"], 2, "d/dx x^3 = 3x^2 = 12 at x = 2."),
        (2, "What is the value of the integral of 2x dx from 0 to 1?", ["0.5", "1", "2", "0"], 1, "Antiderivative x^2, evaluated 1 - 0 = 1."),
        (2, "lim (x->0) sin(x)/x equals", ["0", "1", "Infinity", "Does not exist"], 1, "Standard limit equal to 1."),
        (3, "For f(x, y) = x^2 y + y^3, what is the partial derivative with respect to y?", ["2xy + 3y^2", "x^2 + 3y^2", "x^2 + y^2", "2x + 3y^2"], 1, "Treat x as constant: x^2 + 3y^2."),
    ],
    "linear_algebra": [
        (1, "Multiplying a 2x3 matrix by a 3x4 matrix gives a matrix of size", ["3x3", "2x4", "4x2", "Not defined"], 1, "Outer dimensions: 2x4."),
        (2, "What is the determinant of [[2, 1], [4, 3]]?", ["2", "10", "-2", "5"], 0, "2*3 - 1*4 = 2."),
        (2, "What is the rank of [[1, 2], [2, 4]]?", ["0", "1", "2", "4"], 1, "Second row is twice the first, so rank 1."),
        (3, "The eigenvalues of [[2, 0], [0, 3]] are", ["0 and 5", "2 and 3", "1 and 6", "6 only"], 1, "Diagonal matrix: eigenvalues are the diagonal entries."),
    ],
    "prob_stats": [
        (1, "A fair coin is tossed twice. What is P(both heads)?", ["1/2", "1/3", "1/4", "3/4"], 2, "(1/2)*(1/2) = 1/4."),
        (2, "What is the mean of 2, 4, 6, 8?", ["4", "5", "6", "20"], 1, "Sum 20 / 4 = 5."),
        (2, "A and B are independent with P(A) = 0.5 and P(B) = 0.4. P(A and B) is", ["0.9", "0.1", "0.2", "0.45"], 2, "Independent: 0.5 * 0.4 = 0.2."),
        (3, "In a normal distribution, roughly what share of values lie within one standard deviation of the mean?", ["50%", "68%", "95%", "99.7%"], 1, "Empirical rule: about 68%."),
    ],
    "numerical_methods": [
        (1, "The Newton-Raphson method is mainly used to", ["Integrate functions", "Find roots of equations", "Sort data", "Invert matrices exactly"], 1, "It iterates x - f(x)/f'(x) towards a root."),
        (2, "Using the trapezoidal rule with a single interval, integral of f(x) = x from 0 to 2 is", ["1", "2", "4", "0"], 1, "(b-a)/2*(f(a)+f(b)) = 1*(0+2) = 2."),
        (2, "One explicit Euler step (h = 0.1) for dy/dx = y with y(0) = 1 gives y(0.1) =", ["1.0", "1.1", "1.105", "0.9"], 1, "y1 = y0 + h*y0 = 1.1."),
        (3, "Gauss-Seidel iteration is guaranteed to converge when the coefficient matrix is", ["Singular", "Strictly diagonally dominant", "Upper triangular only", "Skew-symmetric"], 1, "Strict diagonal dominance is a sufficient condition."),
    ],
    "prog_fund": [
        (1, "In Python, what does print(7 // 2) output?", ["3.5", "3", "4", "1"], 1, "// is floor division."),
        (2, "What does len([1, [2, 3], 4]) return?", ["4", "3", "2", "Error"], 1, "The nested list counts as one element."),
        (2, "How many times does `for i in range(1, 10, 3):` run?", ["3", "4", "9", "10"], 0, "i takes 1, 4, 7."),
        (3, "x = [1, 2, 3]; y = x; y.append(4). What is len(x)?", ["3", "4", "Error", "0"], 1, "x and y reference the same list."),
    ],
    "oop": [
        (1, "Encapsulation means", ["Bundling data with the methods that use it and restricting direct access", "Running code in parallel", "Converting objects to JSON", "Using many global variables"], 0, "Encapsulation hides internal state behind methods."),
        (2, "Method overriding requires", ["Two methods with different names", "A subclass redefining a method of its superclass", "Static methods only", "Operator overloading"], 1, "Overriding happens across an inheritance relationship."),
        (2, "Which is an example of polymorphism?", ["A variable changing type", "The same method call behaving differently for different object types", "A class with private fields", "A loop over a list"], 1, "One interface, many implementations."),
        (3, "'Favour composition over inheritance' mainly aims to reduce", ["Memory use", "Tight coupling between classes", "Number of files", "Compile time"], 1, "Composition keeps classes loosely coupled."),
    ],
    "discrete_math": [
        (1, "How many subsets does a 4-element set have?", ["8", "16", "4", "24"], 1, "2^4 = 16."),
        (2, "The negation of 'for all x, P(x)' is", ["For all x, not P(x)", "There exists x such that not P(x)", "There exists x such that P(x)", "Not for any x"], 1, "Negating a universal gives an existential."),
        (2, "How many edges does the complete graph K5 have?", ["5", "10", "20", "25"], 1, "5*4/2 = 10."),
        (3, "In how many ways can 3 people be chosen from 6?", ["18", "20", "120", "216"], 1, "C(6,3) = 20."),
    ],
    "dsa": [
        (1, "A stack follows which order?", ["FIFO", "LIFO", "Random", "Priority"], 1, "Last in, first out."),
        (2, "Worst-case time of binary search on a sorted array of n elements is", ["O(n)", "O(log n)", "O(n log n)", "O(1)"], 1, "The search space halves each step."),
        (2, "Average-case time complexity of quicksort is", ["O(n^2)", "O(n log n)", "O(n)", "O(log n)"], 1, "Balanced partitions on average."),
        (3, "Single-source shortest paths in a graph with non-negative edge weights is best solved by", ["DFS", "Dijkstra's algorithm", "Kruskal's algorithm", "Topological sort"], 1, "Dijkstra requires non-negative weights."),
        (3, "BFS on an unweighted graph finds", ["A minimum spanning tree", "Shortest paths in number of edges", "Strongly connected components", "A topological order"], 1, "BFS explores level by level."),
    ],
    "databases": [
        (1, "Which SQL command retrieves rows from a table?", ["INSERT", "SELECT", "UPDATE", "CREATE"], 1, "SELECT queries data."),
        (2, "A primary key", ["Can contain duplicates", "Uniquely identifies each row and cannot be NULL", "Must be a string", "Is optional in every relation"], 1, "Primary keys are unique and non-null."),
        (2, "Which clause filters groups after aggregation?", ["WHERE", "ORDER BY", "HAVING", "LIMIT"], 2, "HAVING applies after GROUP BY."),
        (3, "Which ACID property ensures committed changes survive a crash?", ["Atomicity", "Consistency", "Isolation", "Durability"], 3, "Durability persists committed transactions."),
        (2, "Which join returns all rows of the left table even without a match?", ["INNER JOIN", "LEFT JOIN", "CROSS JOIN", "SELF JOIN"], 1, "LEFT JOIN keeps unmatched left rows with NULLs."),
    ],
    "os": [
        (1, "Threads of the same process share", ["Their stack", "The address space", "Their program counter", "Nothing"], 1, "Threads share code, data and heap."),
        (2, "Which is NOT one of the four necessary conditions for deadlock?", ["Mutual exclusion", "Hold and wait", "Circular wait", "Preemption"], 3, "The condition is NO preemption."),
        (2, "A page fault occurs when", ["The CPU overheats", "A referenced page is not in physical memory", "A file is deleted", "Two threads share data"], 1, "The OS must load the page from disk."),
        (3, "Round-robin scheduling with a very large time quantum behaves like", ["SJF", "FCFS", "Priority scheduling", "Multilevel queue"], 1, "Each job runs to completion in arrival order."),
    ],
    "networks": [
        (1, "The default port for HTTP is", ["21", "80", "443", "25"], 1, "HTTP uses port 80 (HTTPS 443)."),
        (2, "Compared with UDP, TCP provides", ["Lower latency always", "Reliable, ordered delivery", "Broadcast support", "No connection setup"], 1, "TCP is connection-oriented and reliable."),
        (2, "DNS translates", ["IP addresses to MAC addresses", "Domain names to IP addresses", "HTTP to HTTPS", "Ports to sockets"], 1, "DNS resolves names to addresses."),
        (3, "How many usable host addresses are there in a /24 IPv4 subnet?", ["256", "254", "255", "128"], 1, "2^8 - 2 (network and broadcast) = 254."),
    ],
    "software_eng": [
        (1, "Which git command records staged changes to the repository history?", ["git push", "git commit", "git clone", "git status"], 1, "commit records a snapshot."),
        (2, "A unit test", ["Tests the whole deployed system", "Tests a single function or class in isolation", "Is written only after release", "Measures performance"], 1, "Unit tests isolate small units."),
        (2, "In Scrum, a sprint is", ["A bug report", "A short time-boxed development iteration", "A deployment server", "A code review tool"], 1, "Sprints are typically 1-4 weeks."),
        (3, "Which design pattern ensures a class has only one instance?", ["Factory", "Observer", "Singleton", "Adapter"], 2, "Singleton restricts instantiation to one object."),
    ],
    "web_dev": [
        (1, "HTML stands for", ["HyperText Markup Language", "High Transfer Machine Language", "Hyperlink Text Mode Language", "Home Tool Markup Language"], 0, ""),
        (2, "Which HTTP method is normally used to fetch a resource without side effects?", ["POST", "GET", "DELETE", "PATCH"], 1, "GET is safe and idempotent."),
        (2, "HTTP status 404 means", ["Server error", "Unauthorized", "Not Found", "Redirect"], 2, ""),
        (3, "Which status code best indicates a resource was successfully created by a REST API?", ["200", "201", "204", "302"], 1, "201 Created."),
    ],
    "data_analysis": [
        (1, "Which pandas function reads a CSV file?", ["pd.load_csv", "pd.read_csv", "pd.open", "pd.csv"], 1, ""),
        (2, "What is the median of 3, 1, 4, 1, 5?", ["1", "3", "2.8", "4"], 1, "Sorted: 1, 1, 3, 4, 5."),
        (2, "Best chart to show the distribution of one numeric variable?", ["Pie chart", "Histogram", "Line chart over categories", "Scatter of two categories"], 1, ""),
        (3, "df.groupby('dept')['salary'].mean() returns", ["Overall mean salary", "Average salary per department", "Number of departments", "Max salary per department"], 1, ""),
    ],
    "ml": [
        (1, "Supervised learning requires", ["Labelled data", "No data", "Only images", "Reinforcement rewards"], 0, ""),
        (2, "Overfitting is indicated by", ["High training and validation error", "Low training error but high validation error", "Low validation error only", "Equal errors"], 1, "The model memorises training data."),
        (2, "Linear regression is usually fit by minimising", ["Cross-entropy", "Mean squared error", "Hinge loss", "Accuracy"], 1, ""),
        (3, "Precision is defined as", ["TP / (TP + FN)", "TP / (TP + FP)", "(TP + TN) / total", "FP / (FP + TN)"], 1, "Of predicted positives, how many are correct."),
        (3, "The main purpose of k-fold cross-validation is to", ["Speed up training", "Estimate generalisation performance", "Increase dataset size", "Remove outliers"], 1, ""),
    ],
    "thermodynamics": [
        (1, "The first law of thermodynamics expresses", ["Conservation of energy", "Increase of entropy", "Absolute zero is unattainable", "Thermal equilibrium"], 0, ""),
        (2, "Carnot efficiency of an engine between 600 K and 300 K is", ["25%", "50%", "75%", "100%"], 1, "1 - 300/600 = 0.5."),
        (2, "For an isolated system undergoing an irreversible process, entropy", ["Decreases", "Stays constant", "Increases", "Becomes zero"], 2, "Second law."),
        (3, "For an ideal gas in an isothermal process, the change in internal energy is", ["Positive", "Negative", "Zero", "Equal to work done"], 2, "U depends only on T for an ideal gas."),
    ],
    "fluid_mechanics": [
        (1, "Reynolds number is the ratio of", ["Inertial to viscous forces", "Pressure to gravity forces", "Viscous to surface tension forces", "Heat to mass transfer"], 0, ""),
        (2, "Flow in a circular pipe is typically laminar when Re is below about", ["100", "2100", "10,000", "1,000,000"], 1, "Laminar up to roughly 2000-2300."),
        (2, "Bernoulli's equation assumes", ["Unsteady compressible viscous flow", "Steady, incompressible, inviscid flow along a streamline", "Turbulent flow only", "Two-phase flow"], 1, ""),
        (3, "For incompressible flow, if a pipe's cross-section area halves, the velocity", ["Halves", "Doubles", "Stays the same", "Quadruples"], 1, "Continuity: A1V1 = A2V2."),
    ],
    "heat_transfer": [
        (1, "Which mode of heat transfer needs no medium?", ["Conduction", "Convection", "Radiation", "Advection"], 2, ""),
        (2, "Fourier's law relates heat flux to", ["Velocity", "Temperature gradient", "Pressure drop", "Concentration gradient"], 1, "q = -k dT/dx."),
        (2, "Units of the convective heat transfer coefficient are", ["W/m.K", "W/m^2.K", "J/kg.K", "W"], 1, ""),
        (3, "For a plane wall with fixed k and temperature difference, doubling the thickness makes the heat flux", ["Double", "Halve", "Unchanged", "Quadruple"], 1, "Flux is inversely proportional to thickness."),
    ],
    "mass_transfer": [
        (1, "Fick's law describes", ["Molecular diffusion", "Radiation", "Viscous flow", "Chemical kinetics"], 0, ""),
        (2, "Distillation separates components based on differences in", ["Density", "Volatility", "Colour", "Particle size"], 1, ""),
        (2, "The Schmidt number is the ratio of", ["Momentum diffusivity to mass diffusivity", "Thermal to mass diffusivity", "Inertia to viscosity", "Convective to diffusive heat transfer"], 0, "Sc = nu / D."),
        (3, "In a counter-current gas absorber, increasing the liquid flow rate (all else fixed) generally", ["Reduces solute removal", "Increases solute removal", "Has no effect", "Stops absorption"], 1, "A higher L/G ratio increases the driving force."),
    ],
    "reaction_eng": [
        (1, "A reaction with rate r = k C_A^2 is of order", ["Zero", "First", "Second", "Third"], 2, ""),
        (2, "The Arrhenius equation relates the rate constant to", ["Pressure", "Temperature", "Volume", "Catalyst mass only"], 1, "k = A exp(-Ea/RT)."),
        (2, "For a first-order reaction, the half-life", ["Depends on initial concentration", "Is independent of initial concentration", "Is always zero", "Increases with conversion"], 1, "t1/2 = ln2 / k."),
        (3, "For a positive-order reaction at the same conversion, compared with a CSTR, an ideal PFR needs", ["A larger volume", "A smaller volume", "The same volume", "Infinite volume"], 1, "A PFR operates at higher average concentration."),
    ],
    "process_control": [
        (1, "Feedback control works by", ["Measuring disturbances only", "Comparing the measured output with the setpoint", "Fixing the valve position", "Using only a model"], 1, ""),
        (2, "Integral action in a PID controller removes", ["Noise", "Steady-state offset", "Overshoot completely", "Dead time"], 1, ""),
        (2, "The transfer function of a first-order system is", ["K/(tau s + 1)", "K s", "K/s^2", "K(tau s + 1)"], 0, ""),
        (3, "The Laplace transform of a unit step is", ["1", "1/s", "s", "1/s^2"], 1, ""),
    ],
    "solid_mechanics": [
        (1, "Normal stress is defined as", ["Force x area", "Force / area", "Area / force", "Force / length"], 1, ""),
        (2, "Hooke's law states that within the elastic limit", ["Stress is proportional to strain", "Strain is constant", "Stress is zero", "Deformation is permanent"], 0, ""),
        (2, "The SI unit of Young's modulus is", ["N", "Pa", "m", "J"], 1, ""),
        (3, "Maximum bending moment in a simply supported beam of span L with central point load P is", ["PL/2", "PL/4", "PL/8", "PL"], 1, ""),
    ],
    "manufacturing": [
        (1, "Casting involves", ["Pouring molten metal into a mould", "Removing chips with a tool", "Joining two parts", "Rolling sheets"], 0, ""),
        (2, "Which process removes material using a rotating multi-point cutter?", ["Turning", "Milling", "Casting", "Forging"], 1, ""),
        (2, "Which welding process uses a non-consumable tungsten electrode?", ["MIG", "TIG (GTAW)", "SMAW", "Gas welding"], 1, ""),
        (3, "In Taylor's tool life equation V T^n = C, increasing cutting speed V", ["Increases tool life", "Decreases tool life", "Does not affect tool life", "Makes n negative"], 1, ""),
    ],
    "machine_design": [
        (1, "Factor of safety is the ratio of", ["Failure stress to allowable (working) stress", "Load to area", "Strain to stress", "Weight to volume"], 0, ""),
        (2, "Fatigue failure is caused by", ["A single static overload", "Cyclic, fluctuating loads", "High temperature only", "Corrosion only"], 1, ""),
        (2, "The main purpose of a key on a shaft is to", ["Reduce weight", "Transmit torque between shaft and hub", "Lubricate the bearing", "Increase speed"], 1, ""),
        (3, "For ductile materials under combined loading, the most commonly used failure theory is", ["Maximum principal stress", "Maximum distortion energy (von Mises)", "Maximum strain energy", "Rankine"], 1, ""),
    ],
    "cad_modelling": [
        (1, "Orthographic projection shows an object using", ["One 3D view", "Multiple 2D views such as front, top and side", "Perspective only", "A photo"], 1, ""),
        (2, "In parametric CAD, dimensions", ["Are only annotations", "Drive the geometry and can be edited to update the model", "Cannot be changed", "Are added after printing"], 1, ""),
        (2, "In first-angle projection, the top view is placed", ["Above the front view", "Below the front view", "Left of the front view", "Anywhere"], 1, ""),
        (3, "In GD&T, flatness is a", ["Location tolerance", "Form tolerance", "Orientation tolerance", "Runout tolerance"], 1, ""),
    ],
    "material_energy_balance": [
        (1, "For a steady-state process with no reaction, total mass input equals", ["Zero", "Total mass output", "Accumulation", "Generation"], 1, ""),
        (2, "100 kg/h of a 20% NaCl solution is evaporated to 50% NaCl. How much water is removed?", ["40 kg/h", "50 kg/h", "60 kg/h", "80 kg/h"], 2, "Salt 20 kg; final mass 40 kg; 60 kg water removed."),
        (2, "Mixing 50 kg of 10% sugar solution with 50 kg of 30% sugar solution gives a concentration of", ["15%", "20%", "25%", "40%"], 1, "20 kg sugar in 100 kg."),
        (3, "A 'basis of calculation' in balance problems is", ["The final answer", "A chosen reference amount or time on which calculations are based", "The units used", "The reactor type"], 1, ""),
    ],
    "research_methods": [
        (1, "A research hypothesis is", ["A proven fact", "A testable prediction", "A literature summary", "A dataset"], 1, ""),
        (2, "A p-value below 0.05 usually means", ["The null hypothesis is true", "Reject the null hypothesis at the 5% level", "The effect is large", "The experiment failed"], 1, ""),
        (2, "The main purpose of a literature review is to", ["Copy prior results", "Identify existing work and gaps", "Format citations", "Increase word count"], 1, ""),
        (3, "A confounding variable is one that", ["Is measured last", "Influences both the independent and dependent variables", "Has no variance", "Is always categorical"], 1, ""),
    ],
    "tech_writing": [
        (1, "An abstract is", ["The reference list", "A concise summary of the whole paper", "The first experiment", "An appendix"], 1, ""),
        (2, "Good technical writing practice is to", ["Use synonyms for key terms to add variety", "Define terms and use them consistently", "Avoid figures", "Write long sentences"], 1, ""),
        (2, "Plagiarism is best avoided by", ["Paraphrasing without credit", "Citing sources properly", "Using fewer sources", "Avoiding quotes entirely"], 1, ""),
        (3, "IMRaD stands for", ["Introduction, Methods, Results and Discussion", "Ideas, Models, Reports and Data", "Introduction, Motivation, Review and Data", "Index, Methods, References and Diagrams"], 0, ""),
    ],
    "polity_governance": [
        (1, "The Constitution of India came into force on", ["15 August 1947", "26 January 1950", "26 November 1949", "2 October 1950"], 1, ""),
        (2, "Fundamental Rights are contained in which Part of the Constitution?", ["Part II", "Part III", "Part IV", "Part V"], 1, ""),
        (2, "The President of India is elected by", ["Direct popular vote", "An electoral college of elected members of Parliament and State Legislative Assemblies", "The Lok Sabha only", "The Prime Minister"], 1, ""),
        (3, "Article 21 of the Constitution guarantees", ["Right to equality", "Protection of life and personal liberty", "Freedom of religion", "Right to constitutional remedies"], 1, ""),
        (2, "Directive Principles of State Policy are in", ["Part III", "Part IV", "Part IVA", "Part VI"], 1, ""),
    ],
    "economics": [
        (1, "By the law of demand, when price rises (other things equal), quantity demanded", ["Rises", "Falls", "Is unchanged", "Becomes zero"], 1, ""),
        (2, "GDP measures", ["Government revenue", "Market value of final goods and services produced in a country in a period", "Total exports", "Money supply"], 1, ""),
        (2, "Inflation is", ["A fall in the general price level", "A sustained rise in the general price level", "Rise in one good's price", "Growth in GDP"], 1, ""),
        (3, "In India, the policy repo rate is set by", ["Ministry of Finance", "NITI Aayog", "RBI's Monetary Policy Committee", "SEBI"], 2, ""),
    ],
    "history_society": [
        (1, "The Dandi March (Salt Satyagraha) took place in", ["1920", "1930", "1942", "1919"], 1, ""),
        (2, "The Quit India Movement was launched in", ["1940", "1942", "1945", "1935"], 1, ""),
        (2, "The Indian National Congress was founded in", ["1857", "1885", "1905", "1920"], 1, ""),
        (3, "The Permanent Settlement of Bengal (1793) was introduced by", ["Lord Dalhousie", "Lord Cornwallis", "Lord Curzon", "Warren Hastings"], 1, ""),
    ],
    "ethics_aptitude": [
        (1, "A conflict of interest arises when", ["Two officers disagree", "Personal interests could improperly influence official duties", "A policy is unpopular", "A rule is unclear"], 1, ""),
        (2, "Probity in governance primarily means", ["Speed of decisions", "Integrity, honesty and uprightness in public life", "Strict hierarchy", "Use of technology"], 1, ""),
        (2, "Emotional intelligence includes", ["High IQ", "Recognising and managing one's own and others' emotions", "Suppressing all emotions", "Memorising rules"], 1, ""),
        (3, "A whistle-blower is a person who", ["Leads a protest", "Exposes wrongdoing within an organisation", "Audits accounts", "Enforces discipline"], 1, ""),
    ],
    "entrepreneurship": [
        (1, "MVP stands for", ["Most Valuable Player", "Minimum Viable Product", "Maximum Value Proposition", "Market Validation Plan"], 1, ""),
        (2, "Product-market fit means", ["The product is cheap", "The product satisfies strong market demand", "The team is large", "The product has many features"], 1, ""),
        (2, "Customer acquisition cost (CAC) is", ["Revenue per customer", "Sales and marketing cost divided by number of new customers", "Cost of goods sold", "Churn rate"], 1, ""),
        (3, "A startup has Rs 60 lakh in the bank and burns Rs 5 lakh per month. Its runway is", ["6 months", "12 months", "5 months", "30 months"], 1, "60 / 5 = 12."),
    ],
    "product_mgmt": [
        (1, "The standard user-story template is", ["As a <user>, I want <goal> so that <benefit>", "Given/When/Then only", "Feature: Price: Date", "Problem-Solution-Price"], 0, ""),
        (2, "RICE prioritisation stands for", ["Revenue, Impact, Cost, Effort", "Reach, Impact, Confidence, Effort", "Risk, Investment, Cost, Execution", "Reach, Interest, Clarity, Engagement"], 1, ""),
        (2, "An A/B test", ["Compares two variants by randomly splitting users", "Tests two databases", "Is a code review", "Measures uptime"], 0, ""),
        (3, "A north-star metric is", ["Total revenue always", "A single metric that best captures the core value delivered to customers", "Number of employees", "Server uptime"], 1, ""),
    ],
    "business_fundamentals": [
        (1, "The balance-sheet equation is", ["Assets = Liabilities + Equity", "Revenue = Profit + Cost", "Assets = Revenue - Cost", "Equity = Assets + Liabilities"], 0, ""),
        (2, "Revenue 100 and cost of goods sold 60 gives a gross margin of", ["60%", "40%", "160%", "6%"], 1, "(100 - 60)/100."),
        (2, "The break-even point is where", ["Profit is maximised", "Total revenue equals total cost", "Costs are zero", "Sales double"], 1, ""),
        (3, "A positive NPV means the project", ["Loses money", "Is expected to return more than the cost of capital", "Has no risk", "Pays back in one year"], 1, ""),
    ],
    "aptitude": [
        (1, "What is 20% of 150?", ["20", "25", "30", "35"], 2, ""),
        (2, "A 120 m long train runs at 36 km/h. How long does it take to pass a pole?", ["10 s", "12 s", "15 s", "20 s"], 1, "36 km/h = 10 m/s; 120 / 10 = 12 s."),
        (2, "Two numbers are in the ratio 3:5 and sum to 40. The smaller number is", ["12", "15", "25", "8"], 1, ""),
        (3, "A finishes a job in 10 days and B in 15 days. Working together they take", ["5 days", "6 days", "12.5 days", "25 days"], 1, "1/10 + 1/15 = 1/6."),
    ],
}

# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------
GOALS = [
    {
        "id": "software_engineer", "name": "Software / IT role after graduation",
        "description": "Placement-ready for software engineering roles: strong programming, DSA, CS fundamentals and projects.",
        "keywords": ["software", "sde", "developer", "coding", "it role", "programmer", "swe", "tech job", "placement in it", "backend", "frontend", "full stack"],
        "required_skills": [
            {"skill": "prog_fund", "target": 0.8, "importance": 3}, {"skill": "dsa", "target": 0.75, "importance": 3},
            {"skill": "oop", "target": 0.7, "importance": 2}, {"skill": "databases", "target": 0.65, "importance": 2},
            {"skill": "os", "target": 0.6, "importance": 2}, {"skill": "discrete_math", "target": 0.6, "importance": 2},
            {"skill": "software_eng", "target": 0.6, "importance": 2}, {"skill": "networks", "target": 0.5, "importance": 1},
            {"skill": "web_dev", "target": 0.5, "importance": 1}, {"skill": "aptitude", "target": 0.6, "importance": 1},
        ],
        "milestones": [
            {"title": "Solve 150 DSA problems on a coding-practice platform", "kind": "practice", "semester": 5},
            {"title": "Build and deploy one full-stack project (Git, tests, README)", "kind": "project", "semester": 5},
            {"title": "Apply for summer internships (on-campus drive)", "kind": "internship", "semester": 5},
            {"title": "Summer software internship", "kind": "internship", "semester": 6},
            {"title": "Timed DSA mock tests and two mock interviews", "kind": "mock", "semester": 7},
            {"title": "Placement season", "kind": "exam", "semester": 7},
        ],
        "mastery_criteria": ["Score >= 70% on two consecutive timed DSA mock tests", "Complete one end-to-end project with code review", "Clear two mock technical interviews"],
        "recommended_minor": "MIN_CS", "protect_cgpa": False,
    },
    {
        "id": "data_analyst", "name": "Data analytics / data science role",
        "description": "Ready for analyst and junior data-science roles: SQL, statistics, Python data analysis, ML basics and a portfolio project.",
        "keywords": ["data", "analytics", "analyst", "data science", "data scientist", "machine learning", "ml", "ai", "business analyst"],
        "required_skills": [
            {"skill": "data_analysis", "target": 0.8, "importance": 3}, {"skill": "prob_stats", "target": 0.75, "importance": 3},
            {"skill": "databases", "target": 0.7, "importance": 3}, {"skill": "prog_fund", "target": 0.7, "importance": 2},
            {"skill": "linear_algebra", "target": 0.6, "importance": 2}, {"skill": "ml", "target": 0.6, "importance": 2},
            {"skill": "business_fundamentals", "target": 0.4, "importance": 1}, {"skill": "aptitude", "target": 0.6, "importance": 1},
        ],
        "milestones": [
            {"title": "Complete timed SQL and statistics problem sets (>= 70%)", "kind": "practice", "semester": 5},
            {"title": "End-to-end analytics project on an open dataset (published notebook)", "kind": "project", "semester": 5},
            {"title": "Analytics / data internship", "kind": "internship", "semester": 6},
            {"title": "Two mock analyst interviews (case + SQL)", "kind": "mock", "semester": 7},
            {"title": "Placement season", "kind": "exam", "semester": 7},
        ],
        "mastery_criteria": ["Score >= 70% on timed SQL and statistics problem sets", "Complete one end-to-end analytics project", "Clear two mock interviews"],
        "recommended_minor": "", "protect_cgpa": False,
    },
    {
        "id": "higher_studies", "name": "Higher studies: MS / PhD / research career",
        "description": "Strong CGPA, research experience, research-oriented electives, writing skills and test timelines (GRE/TOEFL or GATE).",
        "keywords": ["ms", "phd", "research", "higher studies", "masters", "abroad", "gre", "academia", "professor", "toefl"],
        "required_skills": [
            {"skill": "@programme_core", "target": 0.75, "importance": 3},
            {"skill": "research_methods", "target": 0.75, "importance": 3}, {"skill": "tech_writing", "target": 0.75, "importance": 3},
            {"skill": "linear_algebra", "target": 0.7, "importance": 2}, {"skill": "prob_stats", "target": 0.7, "importance": 2},
            {"skill": "numerical_methods", "target": 0.65, "importance": 2}, {"skill": "prog_fund", "target": 0.6, "importance": 1},
        ],
        "milestones": [
            {"title": "Identify 3 faculty whose research fits your interests and request a UG project", "kind": "research", "semester": 5},
            {"title": "Summer research internship (institute or abroad)", "kind": "internship", "semester": 6},
            {"title": "GRE / TOEFL (or GATE for India) preparation and attempt", "kind": "exam", "semester": 7},
            {"title": "B.Tech project with a written report / paper draft", "kind": "project", "semester": 7},
            {"title": "Statements of purpose, recommendation letters and applications", "kind": "application", "semester": 7},
        ],
        "mastery_criteria": ["Keep CGPA >= 8.0", "Complete a research project with a written report", "Write a 2-page research proposal reviewed by a faculty member"],
        "recommended_minor": "", "protect_cgpa": True,
    },
    {
        "id": "gate_core", "name": "GATE / PSU / M.Tech in own discipline",
        "description": "Clear GATE in the student's branch with a strong rank for M.Tech admissions or PSU jobs.",
        "keywords": ["gate", "psu", "mtech", "m.tech", "iit mtech", "core exam"],
        "required_skills": [
            {"skill": "@programme_core", "target": 0.8, "importance": 3},
            {"skill": "calculus", "target": 0.75, "importance": 2}, {"skill": "linear_algebra", "target": 0.7, "importance": 2},
            {"skill": "prob_stats", "target": 0.65, "importance": 2}, {"skill": "numerical_methods", "target": 0.7, "importance": 2},
            {"skill": "aptitude", "target": 0.75, "importance": 2},
        ],
        "milestones": [
            {"title": "Finish first pass of GATE syllabus for your branch", "kind": "practice", "semester": 6},
            {"title": "Previous-year GATE papers (subject-wise)", "kind": "practice", "semester": 7},
            {"title": "Full-length GATE mock test series", "kind": "mock", "semester": 7},
            {"title": "GATE examination (February)", "kind": "exam", "semester": 8},
        ],
        "mastery_criteria": ["Score >= 60% on three full-length GATE mocks", "Cover every syllabus topic with >= 70% topic quiz accuracy"],
        "recommended_minor": "", "protect_cgpa": True,
    },
    {
        "id": "upsc_cse", "name": "UPSC Civil Services (IAS/IPS)",
        "description": "Build General Studies foundations alongside academics, choose supporting HSS electives, protect CGPA and graduation requirements.",
        "keywords": ["upsc", "ias", "ips", "civil services", "government", "civil service", "ifs", "public service"],
        "required_skills": [
            {"skill": "polity_governance", "target": 0.75, "importance": 3}, {"skill": "history_society", "target": 0.7, "importance": 3},
            {"skill": "economics", "target": 0.7, "importance": 3}, {"skill": "ethics_aptitude", "target": 0.7, "importance": 2},
            {"skill": "tech_writing", "target": 0.6, "importance": 2}, {"skill": "aptitude", "target": 0.7, "importance": 2},
        ],
        "milestones": [
            {"title": "Read NCERT polity, history and economy books (Classes 6-12)", "kind": "practice", "semester": 4},
            {"title": "Daily current-affairs habit and weekly answer-writing", "kind": "practice", "semester": 5},
            {"title": "Choose the optional subject (shortlist via HSS electives)", "kind": "decision", "semester": 6},
            {"title": "Prelims-style mock tests (GS + CSAT)", "kind": "mock", "semester": 7},
            {"title": "First attempt after graduation", "kind": "exam", "semester": 8},
        ],
        "mastery_criteria": ["Score >= 55% on three full-length prelims mocks", "CSAT mock >= 50%", "Weekly answer-writing for 8+ weeks"],
        "recommended_minor": "MIN_HSS", "protect_cgpa": True,
    },
    {
        "id": "startup_founder", "name": "Build and launch a startup",
        "description": "Entrepreneurship, product and business basics plus a validated MVP; connect with the incubation cell and E-cell.",
        "keywords": ["startup", "start-up", "founder", "entrepreneur", "business", "venture", "own company"],
        "required_skills": [
            {"skill": "entrepreneurship", "target": 0.75, "importance": 3}, {"skill": "product_mgmt", "target": 0.65, "importance": 2},
            {"skill": "business_fundamentals", "target": 0.65, "importance": 2}, {"skill": "economics", "target": 0.5, "importance": 1},
            {"skill": "prog_fund", "target": 0.5, "importance": 1}, {"skill": "web_dev", "target": 0.45, "importance": 1},
            {"skill": "tech_writing", "target": 0.5, "importance": 1},
        ],
        "milestones": [
            {"title": "20 customer-discovery interviews", "kind": "project", "semester": 5},
            {"title": "Build an MVP and get 10 real users", "kind": "project", "semester": 6},
            {"title": "Apply to the institute incubation cell / E-cell programmes (outside the buddy)", "kind": "application", "semester": 6},
            {"title": "Pitch at a startup competition", "kind": "mock", "semester": 7},
        ],
        "mastery_criteria": ["Documented 20 customer interviews", "MVP with >= 10 active users", "Pitch deck reviewed by a mentor"],
        "recommended_minor": "MIN_ENT", "protect_cgpa": False,
    },
    {
        "id": "core_engineer", "name": "Core engineering role in own discipline",
        "description": "Placement in a core company (process / design / manufacturing) with strong fundamentals, an industrial internship and a design project.",
        "keywords": ["core", "process engineer", "design engineer", "plant", "manufacturing job", "core company", "core job"],
        "required_skills": [
            {"skill": "@programme_core", "target": 0.75, "importance": 3},
            {"skill": "numerical_methods", "target": 0.6, "importance": 2}, {"skill": "data_analysis", "target": 0.5, "importance": 1},
            {"skill": "aptitude", "target": 0.6, "importance": 1},
        ],
        "milestones": [
            {"title": "Industrial summer internship in a core company", "kind": "internship", "semester": 6},
            {"title": "Design / simulation project in the department", "kind": "project", "semester": 7},
            {"title": "Core-company placement tests and interviews", "kind": "exam", "semester": 7},
        ],
        "mastery_criteria": ["Score >= 70% on core subject quizzes", "Complete an industrial internship report", "Clear a mock technical interview"],
        "recommended_minor": "", "protect_cgpa": False,
    },
    {
        "id": "product_mba", "name": "Product management / MBA (CAT)",
        "description": "Product sense, business fundamentals and CAT-level aptitude for PM roles or MBA admission.",
        "keywords": ["mba", "cat", "product manager", "pm", "management", "consulting", "iim"],
        "required_skills": [
            {"skill": "product_mgmt", "target": 0.7, "importance": 3}, {"skill": "aptitude", "target": 0.8, "importance": 3},
            {"skill": "business_fundamentals", "target": 0.65, "importance": 2}, {"skill": "economics", "target": 0.6, "importance": 2},
            {"skill": "data_analysis", "target": 0.5, "importance": 1}, {"skill": "tech_writing", "target": 0.6, "importance": 1},
        ],
        "milestones": [
            {"title": "Product case competitions / teardown portfolio", "kind": "project", "semester": 5},
            {"title": "Product or consulting internship", "kind": "internship", "semester": 6},
            {"title": "CAT mock series", "kind": "mock", "semester": 7},
            {"title": "CAT examination (November)", "kind": "exam", "semester": 7},
        ],
        "mastery_criteria": ["CAT mock percentile >= 90 on three mocks", "Two product case studies reviewed by a mentor"],
        "recommended_minor": "MIN_ENT", "protect_cgpa": False,
    },
]

PROGRAMMES = [
    {"id": "CHE", "name": "B.Tech Chemical Engineering", "department": "CHE", "total_credits": 160,
     "elective_slots": {"4": {"open_elective": 1}, "5": {"open_elective": 1}, "6": {"open_elective": 1, "dept_elective": 1},
                        "7": {"open_elective": 2, "dept_elective": 1}, "8": {"open_elective": 2, "dept_elective": 1}},
     "core_skills": ["material_energy_balance", "thermodynamics", "fluid_mechanics", "heat_transfer", "mass_transfer", "reaction_eng", "process_control"],
     "source": INST_SRC},
    {"id": "ME", "name": "B.Tech Mechanical Engineering", "department": "ME", "total_credits": 160,
     "elective_slots": {"4": {"open_elective": 1}, "5": {"open_elective": 1}, "6": {"open_elective": 1, "dept_elective": 1},
                        "7": {"open_elective": 2, "dept_elective": 1}, "8": {"open_elective": 2, "dept_elective": 1}},
     "core_skills": ["thermodynamics", "solid_mechanics", "fluid_mechanics", "heat_transfer", "manufacturing", "machine_design", "process_control"],
     "source": INST_SRC},
]

MINORS = [
    {"id": "MIN_CS", "name": "Minor in Computer Science", "department": "CSE", "min_cgpa": 7.5, "credits_required": 16,
     "courses": ["CS102", "CS201", "CS202", "CS203", "CS204", "CS301", "CS302", "CS303", "CS304"], "excluded_programmes": ["CSE"], "source": INST_SRC},
    {"id": "MIN_HSS", "name": "Minor in Economics and Public Policy", "department": "HSS", "min_cgpa": 7.0, "credits_required": 12,
     "courses": ["HS201", "HS202", "HS203", "HS204"], "excluded_programmes": [], "source": INST_SRC},
    {"id": "MIN_ENT", "name": "Minor in Entrepreneurship and Management", "department": "MGMT", "min_cgpa": 6.5, "credits_required": 12,
     "courses": ["MS201", "MS202", "MS203", "HS201"], "excluded_programmes": [], "source": INST_SRC},
]

RULES = [
    {"key": "max_credits_per_semester", "value": 24, "description": "Normal maximum registered credits in a regular semester", "source": INST_SRC},
    {"key": "overload", "value": {"min_cgpa": 8.0, "max_credits": 28}, "description": "Students with CGPA >= 8.0 may register up to 28 credits", "source": INST_SRC},
    {"key": "min_credits_per_semester", "value": 12, "description": "Minimum registered credits in a regular semester", "source": INST_SRC},
    {"key": "pass_grade", "value": "D", "description": "Minimum passing grade; F is a backlog", "source": INST_SRC},
    {"key": "grade_points", "value": {"A+": 10, "A": 10, "A-": 9, "B": 8, "B-": 7, "C": 6, "C-": 5, "D": 4, "F": 0},
     "description": "Letter grade to grade-point mapping", "source": INST_SRC},
    {"key": "backlog_policy", "value": {"reregister_next_offering": True, "priority_over_electives": True},
     "description": "A failed core course must be re-registered the next time it is offered, before new electives", "source": INST_SRC},
    {"key": "minor_policy", "value": {"from_semester": 4, "max_minors": 1, "cgpa_checked_at_registration": True},
     "description": "Minor courses may be taken from semester 4; CGPA eligibility is checked at registration; one minor at most", "source": INST_SRC},
    {"key": "minor_courses_as_open_electives", "value": True,
     "description": "Courses from another department's minor list may fill open-elective slots", "source": INST_SRC},
    {"key": "online_credit", "value": {"max_courses": 2, "counts_as": "open_elective", "requires": "Proctored NPTEL/SWAYAM exam certificate", "max_credits": 6},
     "description": "Up to two online NPTEL/SWAYAM courses (max 6 credits) may be credited as open electives with a proctored exam certificate",
     "source": INST_SRC + "; UGC (Credit Framework for Online Learning Courses through SWAYAM) Regulations, 2021"},
    {"key": "semester_calendar", "value": {"weeks": 16, "midsem_week": 8, "endsem_weeks": [15, 16], "exam_week_capacity": 0.5,
                                           "odd": "Jul-Nov", "even": "Jan-Apr"},
     "description": "Teaching weeks and exam weeks; self-study capacity halves in exam weeks", "source": INST_SRC},
    {"key": "total_semesters", "value": 8, "description": "Regular B.Tech duration in semesters", "source": INST_SRC},
]

EVIDENCE_WEIGHTS = {
    "assessment": 1.0, "mock": 1.0, "project": 0.9, "exercise": 0.8, "grade": 0.6, "self": 0.2,
}
RULES.append({"key": "evidence_reliability", "value": EVIDENCE_WEIGHTS,
              "description": "Reliability weight of each evidence source used by the mastery model (product decision)", "source": "Learning Buddy design"})
RULES.append({"key": "mastery_thresholds", "value": {"min_confidence": 0.55, "require_tested_evidence": True},
              "description": "A skill counts as demonstrated only with enough confidence and at least one tested (assessment/exercise/project/mock) evidence item",
              "source": "Learning Buddy design"})


def write_csv(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_json(name, obj):
    with open(OUT / name, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    write_csv("skills.csv", ["id", "name", "category", "prereq_skills", "description"],
              [(s[0], s[1], s[2], s[3], s[4]) for s in SKILLS])
    write_csv("courses.csv",
              ["code", "title", "department", "credits", "offered", "course_type", "mode", "programme", "semester",
               "weekly_hours", "syllabus", "objectives", "source", "last_verified"],
              [(*c, ONLINE_SRC.get(c[0], INST_SRC), VERIFIED) for c in COURSES])
    write_csv("prerequisites.csv", ["course_code", "prereq_code", "min_grade"], [(a, b, "D") for a, b in PREREQS])
    write_csv("course_skills.csv", ["course_code", "skill_id", "level"],
              [(c, s, lvl) for c, lst in COURSE_SKILLS.items() for s, lvl in lst])
    write_csv("resources.csv",
              ["id", "title", "provider", "url", "skill_ids", "format", "level", "est_hours", "license", "credit_eligible"],
              [(*r[:9], str(r[9]).lower()) for r in RESOURCES])

    # modules: link each to the course that teaches the skill best and to a resource
    best_course = {}
    for c, lst in COURSE_SKILLS.items():
        for s, lvl in lst:
            if s not in best_course or lvl > best_course[s][1]:
                best_course[s] = (c, lvl)
    res_by_skill = {}
    for r in RESOURCES:
        for s in r[4].split(","):
            res_by_skill.setdefault(s, []).append(r)
    rows = []
    for skill, mods in MODULES.items():
        res = res_by_skill.get(skill, [])
        for i, (title, level, kind, hours) in enumerate(mods, 1):
            # pick a resource whose level is closest to the module level
            r = min(res, key=lambda x: abs(x[6] - level)) if res else None
            rows.append((f"M_{skill}_{i:02d}", best_course.get(skill, ("", 0))[0], skill, title, i, level, kind, hours,
                         r[0] if r else "", f"Authored from syllabus of {best_course.get(skill, ('',))[0] or 'open resources'}"
                         + (f" and {r[1]}" if r else "")))
    write_csv("modules.csv", ["id", "course_code", "skill_id", "title", "seq", "level", "kind", "est_hours", "resource_id", "source"], rows)

    qs = []
    for skill, items in Q.items():
        for i, (d, prompt, opts, ans, expl) in enumerate(items, 1):
            qs.append({"id": f"Q_{skill}_{i:02d}", "skill_id": skill, "difficulty": d,
                       "kind": "diagnostic" if i <= 4 else "practice", "qtype": "mcq",
                       "prompt": prompt, "options": opts, "answer": opts[ans], "explanation": expl,
                       "source": "Authored by the team from standard syllabus content; reviewed for a single correct answer"})
    write_json("questions.json", qs)
    write_json("goals.json", GOALS)
    write_json("programmes.json", PROGRAMMES)
    write_json("minors.json", MINORS)
    write_json("rules.json", RULES)
    print(f"skills={len(SKILLS)} courses={len(COURSES)} modules={len(rows)} resources={len(RESOURCES)} questions={len(qs)}")


if __name__ == "__main__":
    main()
