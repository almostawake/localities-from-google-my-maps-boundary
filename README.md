# Get localities inside a boundary drawn in Google My Map

Turns **this** — a layer you draw in Google MyMaps:

![My Map](docs/my-map.png)

**Into this** — a spreadsheet of localities and driving time from a place of your choice (in my case Bowral):

![Sample output](docs/sample-output.png)

---

## Pre-requisites

- **Python** (to run this code)

  To check if you have it run this in the "terminal" app:

  `python3 --version`

  If it’s missing, install from [python.org](https://www.python.org/downloads/) or another way if you prefer.

- A **gmail account** (does the actual lookups and calculations ).

---

## 1. Get the project

On GitHub, click **Code** → **Download ZIP**. Unzip the file and open a terminal in the resulting folder.

(Or clone with Git if you prefer: `git clone <repository-url>` then `cd <repository-folder>`.)

You should see at least:

- `getLocationsInMyMap.py` – main script
- `requirements.txt` – Python dependencies
- `.env.example` – template for your API key

---

## 2. Draw your area in Google My Maps

You define the “service area” as a **single polygon** in Google My Maps, then export it as KML.

### 2.1 Open My Maps

1. Go to [Google My Maps](https://www.google.com/maps/d/).
2. Sign in with your Google account.
3. Click **Create a new map**.

### 2.2 Add a layer and draw the polygon

1. The map opens with an untitled layer. Click **Untitled layer** and give it a name (e.g. “Service area”).
2. Under the search bar, click **Draw a line** (the third icon).
3. Choose **Add line or shape**.
4. Click on the map to place the **first point** of your boundary.
5. Click to add more points. Each click adds a vertex. Draw around the full area you care about.
6. To **close the shape**, click again on (or very near) the **first point**. The shape will fill and become a polygon.
7. When asked, give the shape a name (e.g. “Service area”) and click **Save**.

You should see one closed, filled polygon. That’s your area. You can edit it later (click the shape → Edit) or add more shapes, but **this script uses only the first polygon** in the first layer.

### 2.3 Export the map as KML

1. Click the **three dots (⋮)** next to your map title (top of the left panel).
2. Click **Export to KML/KMZ**.
3. In the export dialog:
   - Leave **Export as KML** (not KMZ) if the option exists; otherwise KMZ is fine (the script expects KML content; if you only get KMZ, rename the downloaded file to `myMap.kmz` and we’d need a small script change to unzip it – for simplicity, choose KML if available).
   - Ensure the **layer with your polygon** is checked.
4. Download the file. If you only get **KMZ**, unzip it; inside you’ll find a `.kml` file—use that.
5. **Rename the file to `myMap.kml`** (if it isn’t already).
6. **Move `myMap.kml`** into the project folder (the same folder as `getLocationsInMyMap.py`).

Screenshots for these steps can go in `docs/images/` (e.g. `docs/images/my-map-draw-polygon.png`, `docs/images/my-map-export-kml.png`) and be linked from here.

---

## 3. Set up Google Cloud (APIs and key)

The script uses several Google APIs. You enable them in one project and use one API key.

### 3.1 Create or select a project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Sign in with the same Google account.
3. In the top bar, click the **project dropdown** (“Select a project” or the current project name).
4. Click **New project**, give it a name (e.g. “My Map localities”), and click **Create**. Or select an existing project.

### 3.2 Enable billing

Google Cloud requires billing to be enabled on the project, but the APIs used here have free tiers; you only pay if you exceed them.

1. In the left menu, go to **Billing**.
2. Link a billing account to this project (or create one). You may need to add a payment method.

### 3.3 Enable the four APIs

The script needs exactly these APIs. Enable each one:

1. In the left menu, go to **APIs & services** → **Library** (or “Enable APIs and Services”).
2. Search for and enable each of the following (click the API name, then **Enable**):

   | API name (search for this)                    | Used for                              |
   | --------------------------------------------- | ------------------------------------- |
   | **Places Aggregate API** (or “Area Insights”) | Localities inside your polygon        |
   | **Places API**                                | Place names and coordinates           |
   | **Geocoding API**                             | Resolving “Bowral, NSW, Australia”    |
   | **Distance Matrix API** (Legacy)              | Driving distance and time from Bowral |

3. Repeat until all four are enabled for this project.

### 3.4 Create an API key

1. Go to **APIs & services** → **Credentials**.
2. Click **Create credentials** → **API key**.
3. The key is created. Click **Copy** to copy it (you’ll paste it into `.env` in the next section).
4. (Recommended) Click **Edit API key** (or the key name):
   - Under **Application restrictions**, choose **None** (or **IP addresses** and add your machine’s IP if you run the script from one place).  
     Using “HTTP referrers” will block this script, which runs on your machine, not in a browser.
   - Under **API restrictions**, choose **Restrict key** and select only the four APIs listed above.
   - Save.

Keep the key secret. Don’t commit it to Git or share it publicly.

---

## 4. Configure and run the project

### 4.1 Install Python dependencies

In a terminal, in the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4.2 Add your API key

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` in a text editor.
3. Replace `your_google_maps_api_key_here` with your actual API key (paste from step 3.4).
4. Save. Don’t commit `.env` (it should be in `.gitignore`).

### 4.3 Put your KML in place

- Your exported file must be named **`myMap.kml`** and sit in the **same folder** as `getLocationsInMyMap.py`.
- If you exported a different filename, rename it to `myMap.kml`.

### 4.4 Run the script

```bash
python getLocationsInMyMap.py
```

- The script reads `myMap.kml`, calls Google’s APIs (localities in polygon, then place details, then driving distances from Bowral), and writes **`myMap.xlsx`** in the same folder.
- The first run can take a few minutes (many API calls). Progress is printed in the terminal.
- When it finishes, open **`myMap.xlsx`** in Excel or Google Sheets. Columns:
  - **Locality** – place name
  - **Driving distance** – e.g. “45.3 km”
  - **Driving duration (mins)** – integer minutes (for sorting/filtering)

---

## 5. Changing the origin (e.g. not Bowral)

The origin is hard-coded in the script as `ORIGIN = "Bowral, NSW, Australia"`. To use a different starting point:

1. Open `getLocationsInMyMap.py` in a text editor.
2. Find the line with `ORIGIN = "Bowral, NSW, Australia"`.
3. Change it to your address or place name (e.g. `"Sydney, NSW, Australia"`).
4. Save and run the script again.

---

## 6. Troubleshooting

- **“Set GOOGLE_MAPS_API_KEY in .env or environment.”**  
  Create `.env` from `.env.example` and put your API key in it (see 4.2).

- **“No &lt;coordinates&gt; in KML” or file not found.**  
  Ensure the file is named `myMap.kml`, is in the same folder as the script, and was exported from My Maps as KML (one polygon layer).

- **“API keys with referer restrictions cannot be used with this API.”**  
  Edit your API key in Cloud Console → Credentials. Set **Application restrictions** to **None** (or **IP addresses**), not “HTTP referrers”.

- **“REQUEST_DENIED” or “This API project is not authorized to use this API.”**  
  Enable all four APIs in **APIs & services** → **Library** (see 3.3). Wait a few minutes after enabling.

- **Script is slow.**  
  Normal. It issues hundreds of requests (one per locality plus distance matrix batches). Let it run to completion.

---

## Screenshots and extra docs

- Put README screenshots in **`docs/images/`** (e.g. `my-map-draw-polygon.png`, `export-kml.png`, `gcp-enable-api.png`).
- In this README, reference them like:  
  `![Draw polygon](docs/images/my-map-draw-polygon.png)`  
  so they show up when viewing the README on GitHub or elsewhere.

---

## Summary checklist

- [ ] Python 3.9+ and Git installed
- [ ] Project checked out (clone or unzipped)
- [ ] Area drawn in Google My Maps as one polygon and exported as KML
- [ ] File renamed to `myMap.kml` and placed in project folder
- [ ] Google Cloud project created, billing enabled
- [ ] All four APIs enabled (Places Aggregate, Places API, Geocoding, Distance Matrix)
- [ ] API key created and (optional) restricted to those APIs
- [ ] `.env` created from `.env.example` with your API key
- [ ] `pip install -r requirements.txt` run in a venv
- [ ] `python getLocationsInMyMap.py` run; `myMap.xlsx` produced
