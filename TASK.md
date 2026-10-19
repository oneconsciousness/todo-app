Engineering Challenge - “To Do List”
Full Stack (Web)
Build a full‑stack “To Do List” application. Implement both the web frontend client and a
minimal required backend API. Candidates should be prepared to explain their approach
and deep‑dive into their code during a live screen‑sharing session.
Implementation Details
 Backend: Implement a simple backend API (e.g. Node/Express or similar) that supports
the data and operations needed for the To Do List. Backend storage can range from in-
memory or file-based to a full database, as appropriate to your solution. Deployment of
the backend is optional.
 Frontend: Build a web client that connects to your custom backend API and supports
CRUD (Create, Read, Update, Delete) on To Do tasks. The client must allow the user
to log in and perform these operations on their own tasks. The UI must be responsive.
Implement the UI/UX as you see fit. Deployment of the frontend is optional.
Suggested BE hint:
 Prefer a REST-style API (resource URLs, standard HTTP methods, JSON
request/response).
 Use standard HTTP semantics (e.g. 200/201 for success, 400 for validation errors,
401/403 for auth, 404 for missing resource).
Suggested UX hint:
● User should be able to log in from the landing sign in page
● User should be able to see a list of tasks after signing in
● User can change the order of tasks in the list.
● User can search for tasks.
● User can open a task to view or edit it on a task detail screen.
● User can create, update, and delete tasks (full CRUD).

Deliverables
Please take your time to deliver a quality solution that shows your ability. Include:
● A README file that contains:
○ Deployment / running instructions. Assume that we’re running this on a Mac.
Bonus points if instructions are for deployments to a distributed cloud
infrastructure
○ A summary of the assignment

■ Your overall approach
■ What features you completed
■ Given more time, what else would you have liked to complete and how
long it would have taken you?
■ Given more time, what else would you have done to make the project
more robust?
● Production-ready code that:
○ Your code checked into a git repository that can be shared with us (Github,
Gitlab, Bitbucket, etc…). We should be able to run the code
○ Follows community standard syntax and style
○ Has no debug logging, TODOs, or FIXMEs
○ Has test coverage to ensure quality and safety

What we look for
● Clean code. Style we’re looking for: concise but descriptive.
● Enough functionality or code to show us your understanding of fundamental
development practices
● Test coverage for your code using frameworks such as Jest, Mocha, Chai, or Enzyme.
Bonus point if you are able to perform Test Driven Development
● Bonus points: Code in a functional, concise, declarative way. Things we will look for:
higher-order functions, function composition, correct use of basic data structures and
manipulations (map, reduce, apply, etc.)
● Bonus points for managing asynchronous or concurrent execution through high-level
abstractions
NOTE: If your exercise does not meet our minimum grading criteria then we will reach out to cancel this
interview and remaining sessions.