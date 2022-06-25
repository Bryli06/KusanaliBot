
import os
from typing import Optional, Tuple

import tensorflow as tf  # type: ignore
from tensorflow.keras import layers  # type: ignore



def _batch_norm(name: str) -> layers.BatchNormalization:
    return layers.BatchNormalization(
        name=name, epsilon=1e-05,  # Default used in Caffe.
    )


def _conv_block(
        stage: int,
        block: int,
        inputs: tf.Tensor,
        nums_filters: Tuple[int, int, int],
        kernel_size: int = 3,
        stride: int = 2,
) -> tf.Tensor:
    num_filters_1, num_filters_2, num_filters_3 = nums_filters

    conv_name_base = f"conv_stage{stage}_block{block}_branch"
    bn_name_base = f"bn_stage{stage}_block{block}_branch"
    shortcut_name_post = f"_stage{stage}_block{block}_proj_shortcut"
    final_activation_name = f"activation_stage{stage}_block{block}"
    activation_name_base = f"{final_activation_name}_branch"

    shortcut = layers.Conv2D(
        name=f"conv{shortcut_name_post}",
        filters=num_filters_3,
        kernel_size=1,
        strides=stride,
        padding="same"
    )(inputs)

    shortcut = _batch_norm(f"bn{shortcut_name_post}")(shortcut)

    nn = layers.Conv2D(
        name=f"{conv_name_base}2a",
        filters=num_filters_1,
        kernel_size=1,
        strides=stride,
        padding="same"
    )(inputs)
    nn = _batch_norm(f"{bn_name_base}2a")(nn)
    nn = layers.Activation("relu", name=f"{activation_name_base}2a")(nn)

    nn = layers.Conv2D(
        name=f"{conv_name_base}2b",
        filters=num_filters_2,
        kernel_size=kernel_size,
        strides=1,
        padding="same"
    )(nn)
    nn = _batch_norm(f"{bn_name_base}2b")(nn)
    nn = layers.Activation("relu", name=f"{activation_name_base}2b")(nn)

    nn = layers.Conv2D(
        name=f"{conv_name_base}2c",
        filters=num_filters_3,
        kernel_size=1,
        strides=1,
        padding="same"
    )(nn)
    nn = _batch_norm(f"{bn_name_base}2c")(nn)

    nn = layers.Add()([nn, shortcut])

    return layers.Activation("relu", name=final_activation_name)(nn)


def _identity_block(
        stage: int,
        block: int,
        inputs: tf.Tensor,
        nums_filters: Tuple[int, int, int],
        kernel_size: int
) -> tf.Tensor:
    num_filters_1, num_filters_2, num_filters_3 = nums_filters

    conv_name_base = f"conv_stage{stage}_block{block}_branch"
    bn_name_base = f"bn_stage{stage}_block{block}_branch"
    final_activation_name = f"activation_stage{stage}_block{block}"
    activation_name_base = f"{final_activation_name}_branch"

    nn = layers.Conv2D(
        name=f"{conv_name_base}2a",
        filters=num_filters_1,
        kernel_size=1,
        strides=1,
        padding="same"
    )(inputs)
    nn = _batch_norm(f"{bn_name_base}2a")(nn)
    nn = layers.Activation("relu", name=f"{activation_name_base}2a")(nn)

    nn = layers.Conv2D(
        name=f"{conv_name_base}2b",
        filters=num_filters_2,
        kernel_size=kernel_size,
        strides=1,
        padding="same"
    )(nn)
    nn = _batch_norm(f"{bn_name_base}2b")(nn)
    nn = layers.Activation("relu", name=f"{activation_name_base}2b")(nn)

    nn = layers.Conv2D(
        name=f"{conv_name_base}2c",
        filters=num_filters_3,
        kernel_size=1,
        strides=1,
        padding="same"
    )(nn)
    nn = _batch_norm(f"{bn_name_base}2c")(nn)

    nn = layers.Add()([nn, inputs])

    return layers.Activation("relu", name=final_activation_name)(nn)


def make_model(
        input_shape: Tuple[int, int, int] = (224, 224, 3),
        weights_path: Optional[str] = os.path.join(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))), "open_nsfw_weights.h5")
) -> tf.keras.Model:
    image_input = layers.Input(shape=input_shape, name="input")
    nn = image_input

    nn = tf.pad(nn, [[0, 0], [3, 3], [3, 3], [0, 0]], "CONSTANT")
    nn = layers.Conv2D(name="conv_1", filters=64, kernel_size=7, strides=2,
                      padding="valid")(nn)

    nn = _batch_norm("bn_1")(nn)
    nn = layers.Activation("relu")(nn)

    nn = layers.MaxPooling2D(pool_size=3, strides=2, padding="same")(nn)

    nn = _conv_block(stage=0, block=0, inputs=nn,
                    nums_filters=(32, 32, 128),
                    kernel_size=3, stride=1)

    nn = _identity_block(stage=0, block=1, inputs=nn,
                        nums_filters=(32, 32, 128), kernel_size=3)
    nn = _identity_block(stage=0, block=2, inputs=nn,
                        nums_filters=(32, 32, 128), kernel_size=3)

    nn = _conv_block(stage=1, block=0, inputs=nn,
                    nums_filters=(64, 64, 256),
                    kernel_size=3, stride=2)
    nn = _identity_block(stage=1, block=1, inputs=nn,
                        nums_filters=(64, 64, 256), kernel_size=3)
    nn = _identity_block(stage=1, block=2, inputs=nn,
                        nums_filters=(64, 64, 256), kernel_size=3)
    nn = _identity_block(stage=1, block=3, inputs=nn,
                        nums_filters=(64, 64, 256), kernel_size=3)

    nn = _conv_block(stage=2, block=0, inputs=nn,
                    nums_filters=(128, 128, 512),
                    kernel_size=3, stride=2)
    nn = _identity_block(stage=2, block=1, inputs=nn,
                        nums_filters=(128, 128, 512), kernel_size=3)
    nn = _identity_block(stage=2, block=2, inputs=nn,
                        nums_filters=(128, 128, 512), kernel_size=3)
    nn = _identity_block(stage=2, block=3, inputs=nn,
                        nums_filters=(128, 128, 512), kernel_size=3)
    nn = _identity_block(stage=2, block=4, inputs=nn,
                        nums_filters=(128, 128, 512), kernel_size=3)
    nn = _identity_block(stage=2, block=5, inputs=nn,
                        nums_filters=(128, 128, 512), kernel_size=3)

    nn = _conv_block(stage=3, block=0, inputs=nn,
                    nums_filters=(256, 256, 1024), kernel_size=3,
                    stride=2)
    nn = _identity_block(stage=3, block=1, inputs=nn,
                        nums_filters=(256, 256, 1024),
                        kernel_size=3)
    nn = _identity_block(stage=3, block=2, inputs=nn,
                        nums_filters=(256, 256, 1024),
                        kernel_size=3)

    nn = layers.GlobalAveragePooling2D()(nn)

    logits = layers.Dense(name="fc_nsfw", units=2)(nn)
    output = layers.Activation("softmax", name="predictions")(logits)

    model = tf.keras.Model(image_input, output)

    if weights_path is not None:
        model.load_weights(weights_path)
    return model
