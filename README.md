# 🌾 CropSense — AI-Based Crop Recommendation System

CropSense helps farmers choose the right crop for their land. Enter your soil nutrients and local weather, and a machine-learning model recommends the best crop, along with alternatives, crop type, benefits and suggested fertilizers.

**🔗 Live demo:** [cropsense.onrender.com](https://cropsense.onrender.com)

---

## ✨ Features

- **AI crop recommendation** from 7 inputs: Nitrogen (N), Phosphorus (P), Potassium (K), temperature, humidity, pH and rainfall
- **Alternative crops** suggested alongside the top pick
- **Crop insights:** type, advantages and recommended fertilizers for each crop
- **User accounts:** sign up / log in with hashed passwords
- **Recommendation history:** every prediction is saved per user, with optional field labels
- **Responsive UI** built with Tailwind CSS and Lottie animations

## 🧠 How the model works

```
Soil + weather inputs ──► StandardScaler ──► PCA (95% variance) ──► Random Forest ──► Crop
```

| Step | Details |
|---|---|
| Dataset | `dataset/data.csv`: soil and climate readings labelled with 22 crops |
| Preprocessing | Label encoding + standard scaling |
| Dimensionality reduction | PCA keeping 95% of variance |
| Classifier | scikit-learn `RandomForestClassifier` (class-balanced) |
| Split | 80/20 stratified train-test + 5-fold cross-validation |

## 🛠 Tech stack

**Backend:** Python, Flask, Flask-SQLAlchemy, SQLite
**ML:** scikit-learn, NumPy, pandas
**Frontend:** HTML, Jinja2, Tailwind CSS, Bootstrap, Lottie
**Deployment:** Render (gunicorn)

## 📁 Project structure

```
CropSense/
├── app.py              # Flask app: routes, auth, prediction, history
├── train.py            # Trains scaler + PCA + Random Forest, saves to model/
├── predict.py          # Quick command-line prediction test
├── run_init.py         # Creates the SQLite database tables
├── dataset/data.csv    # Training data
├── model/              # Pre-trained .pkl files
├── templates/          # sign.html, index.html, history.html
├── static/             # Images and animations
└── requirements.txt
```

## 🚀 Run it locally

```bash
git clone https://github.com/harshitpoooonia-star/CropSense.git
cd CropSense
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python run_init.py              # create the database
python app.py                   # open http://localhost:10000
```

To retrain the model:

```bash
python train.py
```

Optional: set a `SECRET_KEY` environment variable for sessions in production.

## ☁️ Deploy on Render

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- **Environment variable:** `SECRET_KEY=<any long random string>`

## 👥 Team

Built as a Design Thinking & Innovation (DTI) project at **Bennett University**.

- **Harshit Poonia**
- Shivansh Gupta
- Anaya Bakshi
- Tushita
- Anant Vaibhav

## 📄 License

Released under the [MIT License](LICENSE).
