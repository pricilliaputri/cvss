import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.vgg19 import preprocess_input
from PIL import Image

def load_and_preprocess_image(img_path):
    """
    Load an image and preprocess it for VGG19 model.
    """
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array_expanded_dims = np.expand_dims(img_array, axis=0)
    return preprocess_input(img_array_expanded_dims)

def predict_cataract(model, preprocessed_image):
    """
    Predict whether the image is normal or has cataract.
    """
    prediction = model.predict(preprocessed_image)
    if prediction[0][0] > 0.5:
        return "Cataract detected"
    else:
        return "Normal"

def main():
    # Path to your saved VGG19 model
    model_path = 'modelVgg19.h5'

    # Load the pre-trained VGG19 model
    model = load_model(model_path)

    # Path to the image you want to test
    test_image_path = 'path_to_your_test_image.jpg'

    # Load and preprocess the image
    preprocessed_image = load_and_preprocess_image(test_image_path)

    # Make a prediction
    result = predict_cataract(model, preprocessed_image)
    print(result)

if __name__ == "__main__":
    main()
