class Mirror
  def self.normalize(text)
    text
      .downcase
      .gsub(/[^a-z0-9\s]/i, " ")
      .split
      .reject(&:empty?)
  end
end
