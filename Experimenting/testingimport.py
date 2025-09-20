from joblib import Parallel, delayed

class ParallelProcessor: # Number of jobs for parallel processing

    def square(self, x):
        """Calculates the square of a number."""
        return x ** 3

    def process_numbers(self, numbers):
        """Processes a list of numbers in parallel."""
        print("Processing numbers in parallel...")
        results = Parallel(n_jobs=8)(
            delayed(self.square)(num) for num in numbers
        )
        return results

# Example usage
if __name__ == "__main__":
    processor = ParallelProcessor()
    numbers = [1, 2, 3, 4, 5]
    squared_numbers = processor.process_numbers(numbers)
    print("Squared numbers:", squared_numbers)