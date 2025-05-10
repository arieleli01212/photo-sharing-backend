
FROM python:3.11-slim

# הגדר תיקיית עבודה בתוך הקונטיינר
WORKDIR /app

# העתק את הקבצים המקומיים לתוך הקונטיינר
COPY . .

# התקן את התלויות
RUN pip install --no-cache-dir -r requirements.txt

# הרץ את האפליקציה
CMD ["python","-m", "uvicorn", "main:app"]

