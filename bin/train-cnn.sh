#!/bin/bash

conf=$1
if [ ! -e $conf ]; then
    echo "No config file specified; Exiting."
    exit 1
fi
source $conf

additional_args=${@:2}

echo $layers

viterbi_param=""
if [[ "$viterbi" == "true" ]]; then
    viterbi_param="--viterbi"
fi

layers2_param=""
if [[ "$layers2" != "" ]]; then
    layers2_param="--layers2 \"$layers2\""
fi

doc_param=""
if [[ "$documents" == "true" ]]; then
    doc_param="--documents"
fi

predict_pad_param=""
if [[ "$predict_pad" == "true" ]]; then
    predict_pad_param="--predict_pad"
fi

start_end_param=""
if [[ "$start_end" == "true" ]]; then
    predict_pad_param="--start_end"
fi

load_pretrained_param=""
if [[ "$pretrained_model" != "" ]]; then
    load_pretrained_param="--load_dir $pretrained_model"
fi

cmd="python src/train.py \
--train_dir $train_dir \
--dev_dir $dev_dir \
--maps_dir $maps_dir \
--model_dir $model_dir \
--embed_dim $embedding_dim \
--embeddings $embeddings \
--lstm_dim $num_filters \
--num_filters $num_filters \
--input_dropout $input_dropout \
--hidden_dropout $hidden_dropout \
--input2_dropout $input2_dropout \
--hidden2_dropout $hidden2_dropout \
--middle_dropout $middle_dropout \
--word_dropout $word_dropout \
--lr $lr \
--l2 $l2 \
--batch_size $batch_size \
--nonlinearity $nonlinearity \
--initialization $initialization \
--char_dim $char_dim \
--char_tok_dim $char_tok_dim \
--shape_dim $shape_dim \
--layers \"$layers\" \
--model $model \
--clip_norm $clip_grad \
--regularize_pad_penalty $pad_penalty \
--regularize_drop_penalty $drop_penalty \
--context_regularize_drop_penalty $context_drop_penalty \
--max_additional_pad $max_addl_pad \
--update_frontend $update_frontend \
--frontend_residual_layers $frontend_residuals \
--context_residual_layers $context_residuals \
--projection $do_projection \
--frontend_batch_norm $frontend_batch_norm \
--context_batch_norm $context_batch_norm \
--pad_samples_per_example $pad_samples_per_example \
--margin $margin \
--loss $loss \
--epsilon $epsilon \
--beta2 $beta2 \
--char_model $char_model \
--block_repeats $block_repeats \
--pool_blocks $pool_blocks \
--share_repeats $share_repeats \
--max_epochs $max_epochs \
--fancy_blocks $fancy_blocks \
$doc_param \
$start_end_param \
$predict_pad_param \
$layers2_param \
$viterbi_param \
$load_pretrained_param \
$additional_args"

echo ${cmd}
eval ${cmd}