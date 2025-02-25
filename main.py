import tensorflow as tf
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image


model = tf.keras.models.load_model("traffic-sign.h5")

val = pd.read_csv("signname.csv")

st.title("Display Image from Local System")


uploaded_file = st.file_uploader("Choose an image...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image = image.convert("RGB")
    st.image(image, caption="Uploaded Image", use_column_width=True)
    image = image.resize((32,32))
    imagearr = np.array(image)
    imagearr = np.expand_dims(imagearr,axis=0)

    prediction = model.predict(imagearr)
    pre_class = np.argmax(prediction,axis=1)

    if pre_class[0] == val['ClassId'][pre_class[0]]:
        FINAL = val['SignName'][val['ClassId'][pre_class[0]]]
        st.write(FINAL)
