# -*- coding: utf-8 -*-
"""Weatherforecasting

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1w43moTfioZ11SRjcweMkgX5ThnLwT5pU

1.IMPORT LIBRARIES
"""

import requests
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_squared_error
from datetime import datetime, timedelta
import pytz
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow all origins

@app.route('/api/data')
def get_data():
    return jsonify({"message": "Hello from Flask!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)



"""CURRENT DATA

"""

def get_current_weather(city):
  API_KEY='d1bd306f026eaa97eb3bafc7dcb46423'
  BASE_URL='https://api.openweathermap.org/data/2.5/'
  url=f"{BASE_URL}weather?q={city}&appid={API_KEY}&units=metric"
  response = requests.get(url)
  data = response.json()
  wind_gust_dir = data['wind'].get('deg', None) if 'wind' in data else None
  wind_gust_speed = data['wind'].get('speed', None) if 'wind' in data else None
  feels_like = data['main']['feels_like'] if 'main' in data and 'feels_like' in data['main'] else None
  wind_speed = data['wind'].get('speed', None) if 'wind' in data else None
  wind_direction = data['wind'].get('deg', None) if 'wind' in data else None
  pressure = data['main'].get('pressure', None)
  precipitation = data.get('rain', {}).get('1h', None) or data.get('snow', {}).get('1h', None)
  cloud_coverage = data['clouds'].get('all', None) if 'clouds' in data else None
  weather_condition = data['weather'][0]['main'] if 'weather' in data and data['weather'] else None
  return {
      'city': data['name'],
      'current_temp':round(data['main']['temp']),
      'temp_max': round(data['main']['temp_max']),
      'temp_min': round(data['main']['temp_min']),
      'humidity': round(data['main']['humidity']),
      'description': data['weather'][0]['description'],
      'country': data['sys']['country'],
      'wind_gust_dir': wind_gust_dir,
      'wind_gust_speed': wind_gust_speed,
      'pressure': data['main']['pressure'],
      'feels_like': round(feels_like),
      'wind_speed': wind_speed,
      'precipitation': precipitation,
      'cloud_coverage': cloud_coverage,
      'weather_condition': weather_condition,
      'wind_direction': wind_direction

  }

"""HISTORICAL DATA

"""

def read_prehistorical_data(filename):
  df = pd.read_csv(filename)
  df=df.dropna()
  df=df.drop_duplicates()
  return df

"""data for training"""

def prepare_data(data):
  le=LabelEncoder()
  data['WindGustDir']=le.fit_transform(data['WindGustDir'])
  data['RainTomorrow']=le.fit_transform(data['RainTomorrow'])
  X=data[['MinTemp','MaxTemp','WindGustDir','WindGustSpeed','Humidity','Pressure','Temp']]
  y=data['RainTomorrow']
  return X,y,le

"""Rain prediction

"""

def train_rain_model(X,y):
  X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=0.2,random_state=42)
  model=RandomForestClassifier(n_estimators=100,random_state=42)
  model.fit(X_train,y_train)
  y_pred=model.predict(X_test)
  print("Mean squared Error for rain model")
  print(mean_squared_error(y_test,y_pred))
  return model

"""Regression data"""

def prepare_regression_data(data,feature):
  X,y=[],[]
  for i in range(len(data)-1):
    X.append(data[feature].iloc[i])
    y.append(data[feature].iloc[i+1])
  X=np.array(X).reshape(-1,1)
  y=np.array(y)
  return X,y

"""Regression model"""

def train_regression_model(X,y):
  model=RandomForestRegressor(n_estimators=100,random_state=42)
  model.fit(X,y)
  return model

"""Future prediction"""

def predict_future_weather(model,current_value):
  predictions=[current_value]

  for i in range(5):
    next_value=model.predict(np.array([[predictions[-1]]]))
    predictions.append(next_value[0])
  return predictions[1:]

"""Weather Analysis"""

def weather_view():
  city=input('Enter the city name: ')
  current_weather=get_current_weather(city)

  historical_data=read_prehistorical_data('/weather.csv 2.csv')

  X,y,le=prepare_data(historical_data)

  rain_model=train_rain_model(X,y)
  wind_deg=current_weather['wind_gust_dir']%360
  compass_points=[
      ("N",0,11.25),("NNE",11.25,33.75),("NE",33.75,56.25),("ENE",56.25,78.75),
      ("E",78.75,101.25),("ESE",101.25,123.75),("SE",123.75,146.25),
      ("SSE",146.25,168.75),("S",168.75,191.25),("SSW",191.25,213.75),
      ("SW",213.75,236.25),("WSW",236.25,258.75),("W",258.75,281.25),
      ("WNW",281.25,303.75),("NW",303.75,326.25),("NNW",326.25,348.75)

  ]
  compass_direction=next((point for point,start,end in compass_points if start<=wind_deg<end),'N')
  if compass_direction is None:
      compass_direction_encoded = -1  # Or any other suitable default value
  else:
      compass_direction_encoded=le.transform([compass_direction])[0] if compass_direction in le.classes_ else -1

  current_data={
      'MinTemp': current_weather['temp_min'],
      'MaxTemp': current_weather['temp_max'],
      'WindGustDir': compass_direction_encoded,
      'WindGustSpeed': current_weather['wind_gust_speed'],
      'Humidity': current_weather['humidity'],
      'Pressure': current_weather['pressure'],
      'Temp': current_weather['current_temp']
  }
  current_df=pd.DataFrame([current_data])
  rain_prediction=rain_model.predict(current_df)[0]
  X_temp,y_temp=prepare_regression_data(historical_data,'Temp')
  X_hum,y_hum=prepare_regression_data(historical_data,'Humidity')
  temp_model=train_regression_model(X_temp,y_temp)
  hum_model=train_regression_model(X_hum,y_hum)
  future_temp=predict_future_weather(temp_model,current_weather['temp_min'])
  future_humidity=predict_future_weather(hum_model,current_weather['humidity'])
  timezone=pytz.timezone('Asia/Kolkata')
  now=datetime.now(timezone)
  current_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
  next_hour=now+timedelta(hours=1)
  next_hour=next_hour.replace(minute=0,second=0,microsecond=0)
  future_times=[(next_hour+timedelta(hours=i)).strftime("%H:00") for i in range(5)]
  print(f"City:{city},{current_weather['country']}")
  print(f"Current Date and Time: {current_datetime}")
  print(f"Current Temperature:{current_weather['current_temp']}")
  print(f"Feels like:{current_weather['feels_like']}")
  print(f"Minimum Temperature:{current_weather['temp_min']}°C")
  print(f"Maximum Temperature:{current_weather['temp_max']}°C")
  print(f"Humidity:{current_weather['humidity']}%")
  print(f"Weather Prediction:{current_weather['description']}")
  print(f"Rain Prediction:{'Yes' if rain_prediction else 'No'}")
  print(f"Wind Speed: {current_weather['wind_speed']} m/s")
  print(f"Wind Direction: {current_weather['wind_direction']} degrees")
  print(f"Pressure: {current_weather['pressure']} hPa")
  print(f"Precipitation: {current_weather['precipitation']} mm (last hour)")
  print(f"Cloud Coverage: {current_weather['cloud_coverage']}%")
  print(f"Weather Condition: {current_weather['weather_condition']}")

  print("\nTemperature Forecast:")
  for time,temp in zip(future_times,future_temp):
    print(f"{time}:{round(temp,1)}°C")
  print("\nHumidity Forecast:")
  for time,humidity in zip(future_times,future_humidity):
    print(f"{time}:{round(humidity,1)}%")


weather_view()

import joblib
joblib.dump(model, 'weather_project.pkl')

