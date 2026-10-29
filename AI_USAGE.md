AI Usage Documentation

Tools Used

Anthropic's Claude
Google's Gemini

Prompts Highlights

Could you please look at my seed data, coming from the homework assignments, and please verify what changes should I make to fit my purpose.

Please refresh me over html/css and guide me through so I can learn

I think I dropped my DB. Funnily yes it happened :).

The separate function files could me merged into a single database file? Would it be a better approach than having them separate?

Can i have your opinion over my current logic?

Now that my website is up and working, I want to have it styled. I would like to have rounded corners all around, what should I change? 

Do you like the design ideas I have?

Is it possible to use custom fonts?

I forgot to push

The Benefits

The biggest benefit was speed on repetitive work. Each of the four tables needs the same list, add, edit, and delete pattern, and Claude produced consistent routes, templates, and checked them for me. 

It also helped caught problems I had missed: missing JSON columns, VARCHARs that should have been ENUMs, and a bug in one of my earlier queries where `'text' + CURDATE()` does arithmetic in MySQL instead of joining strings (the fix is `CONCAT()`). It explained errors I ran into such like syntax, and MySQL Workbench warning about JSON syntax. 

For the interface, Claude helped to layout a sort of prototype so I built on it and understood what was going on before any implementation. It also walked me through the Git logic in `config.py`  so the password never reached the repository.

Testing

For each of the four tables I added a record, edited it, and deleted it, and confirmed that the delete popup appears and that cancelling it keeps the record. 

I checked that the dashboard counts changed after those actions and that deleting a company also removed its jobs, contacts, and applications. 

For Job Match I entered skill lists and checked that matching ignores capitalization, that the percentages and the have/missing skills made sense, and that jobs sort by percentage. 

Separately, Claude ran about 150 automated route checks in its own environment using an in-memory stand-in for the database; those files are not part of this repository, so my own runs against MySQL are the real verification. 

Freshly cloned the repo on my desktop computer (windows) and it did work just as it did on my laptop (macOS)

Lessons Learned

I had the opportunity to refresh, learn new things, and put into practice HTML/CSS in this project :). Both Claude and Gemini truly helped me understand code, corrected me many times, and guided my way and my ideas.

On the backend, I learned how a Flask app is organized: routes in `app.py`, templates that extend a shared `base.html`, and a small `database.py` that keeps the connection code in one place. I learned why queries use placeholders (`%s`) instead of putting user input into the SQL string, which protects against SQL injection, and why forms use the post-redirect-get pattern so a refresh doesn't submit them twice. On the database side, how ENUM columns limit a field to valid values, and that MySQL returns JSON columns as text, so Python has to `json.loads` them before the Job Match page can compare skills. On the frontend, I practiced CSS variables for a dark theme, layouts that still work on a phone, and the difference between a design that looks good and one that is readable.

This might be common sense at this very point in life, but keeping an eye on what AI invents is always and marks the difference over what works and what just holds. The AI invented placeholder data, a delete popup could break on a company name with a quote in it, and a design choice (a custom title font) looked worse in the real page than it sounded. 

Finally, I learned practical Git habits though I should have learned this way earlier. It is part of the reason why my commits are not so content rich or controlled at all... however, I learned and I am implementing this on my other class projects!! These habits include: keeping the database password in a git-ignored `config.py` with a `config.example.py` template, checking `git status` before every commit, and pushing in small steps with clear messages.

I truly thank for the chance to learn, the way quizzes and assignments were meant for us to learn, and how this project was being built silently along the way. I truly learned. Thanks a lot Professor!!