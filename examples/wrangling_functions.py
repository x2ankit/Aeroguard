from flight_ad.wrangling import \
    retrieve_all_parameters,\
    map_parameters,\
    change_column_reference,\
    insert_missing_data,\
    resample_dataframe


def preprocess_flight(df_flight, parameter_categories):
    """Preprocess flight. Uses the full flight timeline and maps categorical parameters to numeric values."""
    # Param maps
    param_map = {'WOW': {'GROUND': 0, 'AIR': 1}}

    # Use the entire flight
    df = df_flight[retrieve_all_parameters(parameter_categories)]
    df_filled = insert_missing_data(df, parameter_categories, index=parameter_categories['index'])

    # Map parameters
    output = map_parameters(df_filled, param_map)

    return output


def change_col(df):
    col = 'time'
    df[col] = change_column_reference(df, col, index=0)
    return df.copy()


def resample(df):
    max_no_samples = 282
    return resample_dataframe(df, samples_per_column=max_no_samples)


def preprocess(df):
    parameter_categories = {
        'continuous': ['RALT', 'CAS', 'ALT'],
        'discrete': ['WOW', 'flight_id'],
        'index': ['time']
    }

    return preprocess_flight(df, parameter_categories)


def select(df):
    cols = ['RALT', 'CAS', 'ALT', 'WOW']

    return df[cols]
