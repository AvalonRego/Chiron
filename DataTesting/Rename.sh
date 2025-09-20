cd /viper/ptmp/arego/LargeBio/4000s

# Step 1: Rename all files to temp_x.parquet
for file in *.h5; do
    mv "$file" "temp_$file"
    echo "Renamed: $file" "temp_$file"
done

# Step 2: Rename temp files sequentially
counter=0
for file in $(ls temp_*.h5 | sort -V); do
    mv "$file" "${counter}.h5"
    echo "Renamed: $file -> ${counter}.h5"
    ((counter++))
done

echo "Renaming records completed safely."
cd /viper/ptmp/arego/LargeElectrical/4000s

# Step 1: Rename all files to temp_x.parquet
for file in *.h5; do
    mv "$file" "temp_$file"
    echo "Renamed: $file" "temp_$file"
done

# Step 2: Rename temp files sequentially
counter=0
for file in $(ls temp_*.h5 | sort -V); do
    mv "$file" "${counter}.h5"
    echo "Renamed: $file -> ${counter}.h5"
    ((counter++))
done

echo "Renaming records completed safely."
