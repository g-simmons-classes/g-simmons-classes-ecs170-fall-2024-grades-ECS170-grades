# ECS170 Grade Calculator CLI

A command-line tool for calculating student grades based on assignments, quizzes, and projects, with support for late penalties and weighted categories.

## Dependencies

```bash
pip install rich pyyaml
```

## Usage

```bash
python grade_calculator.py grades.yml policy.yml
```

## Input Files

### Policy File (policy.yml)
Defines grading weights, due dates, and late penalties. Example structure:


### Grades File (grades.yml)
Contains student information and scores. Example structure:
