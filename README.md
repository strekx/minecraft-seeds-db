# minecraft-seeds-db

The purpose of the application is to create a simple and user-friendly collection of interesting Minecraft world seeds. 
The idea comes from my personal interest in Minecraft, as the game was an important part of my childhood. I'm also a member of the _"builders' guild"_ inside the Minecraft community _(as for me, reaching The End is a secondary goal; the main thing is creating cool builds and structures)_, so I, too, want to have a "stockpile" of places where I can build something nice. 

The application just aims to provide a clean and intuitive user interface without advertisements and good UX and accessibility.

## In the app users: 

- can share and discover interesting Minecraft seeds they have found themselves or come across online. 

- can browse the collection of seeds without registering or logging in. 

- can create an account and log in to the application. 

- registered users can add new seeds, as well as edit and delete their own entries. 

- each seed has its own page displaying the seed number, Minecraft version, game edition (Java or Bedrock), starting biome, and description. Registered users can also add information about interesting locations within a world, including their coordinates (e.g. villages, temples, and other structures). 

- users can search for seeds by their seed numbers. 

- users can filter seeds with Minecraft version and game edition. 

- each registered user's profile page displays the number of seeds they have added and a list of their contributions. 

- registered users can save seeds to their favorites and remove them from their favorites. 

- registered users can give their saved favorites custom names and search their favorites using these names. 


## Update 15.11. 
Minimal version of the app is done:

- Users can register, log in and log out.

- Logged-in users can add, edit and delete their own seeds.

- All users can browse the seeds that have been added.

- Seeds can be searched by keyword (title, description, seed number) and filtered by launcher edition (Java / Bedrock) and game version.

- Seed numbers and usernames accept any characters.

## Instructions on running the app locally

1. Clone the repository and open the folder.
2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```
3. Install Flask:
   ```
   pip install flask
   ```
4. Start the app:
   ```
   python app.py
   ```
5. Open http://127.0.0.1:5000 in your browser.

The SQLite database (`minecraft-seeds-db.sqlite`) is not in the repository. The tables are created automatically on first start.

## Testing the app

1. Click "Create new account" and register a user.
2. Sign in, then click "Add seed" and fill in the form.
3. Edit or delete your seed from the front page.
4. Use the search box and the edition/version filters on the front page.
5. Register a second user and check that they cannot edit or delete the first user's seeds.
